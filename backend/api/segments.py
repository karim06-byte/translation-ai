"""Segments API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from backend.models.database import get_db, Segment, Override, User, StyleMemory
from backend.api.schemas import (
    SegmentResponse, SegmentListResponse, OverrideRequest, OverrideResponse, SegmentMetrics
)
from backend.api.auth import get_current_user
from backend.services.style_memory import get_style_memory_service
from backend.services.metrics import get_metrics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/segments", tags=["segments"])


def calculate_and_store_segment_metrics(segment: Segment, db: Session) -> None:
    """Calculate and store metrics for a segment, including word-level change tracking."""
    from backend.services.metrics import get_metrics_service
    metrics_service = get_metrics_service()
    
    if not segment.translated_az:
        return
    
    # Check if segment has override(s)
    all_overrides = db.query(Override).filter(
        Override.segment_id == segment.id
    ).order_by(Override.created_at.asc()).all()  # Get all overrides, oldest first
    
    latest_override = db.query(Override).filter(
        Override.segment_id == segment.id
    ).order_by(Override.created_at.desc()).first()  # Get latest override
    
    # Store original translation source before ANY override (for percentage calculation)
    original_translation_source = segment.translation_source
    original_from_style_memory = segment.from_style_memory
    original_style_similarity = segment.style_similarity_score
    
    if latest_override:
        segment.has_override = True
        
        # Get the FIRST override to find the original translation (before any overrides)
        first_override = all_overrides[0] if all_overrides else latest_override
        original_translation_before_any_override = first_override.old_translation
        
        # Calculate word-level changes between LATEST old and new translation
        # This tells us how much changed in the most recent override
        try:
            import difflib
            # Use the latest override's old and new translations
            old_words = latest_override.old_translation.split() if latest_override.old_translation else []
            new_words = latest_override.new_translation.split() if latest_override.new_translation else []
            
            # Calculate word-level similarity using difflib
            matcher = difflib.SequenceMatcher(None, old_words, new_words)
            word_similarity = matcher.ratio()
            
            # Calculate number of words changed
            total_words = max(len(old_words), len(new_words))
            words_changed = int((1 - word_similarity) * total_words) if total_words > 0 else 0
            
            # Calculate override percentage: how much of the translation was changed in LATEST override (0-100)
            segment.override_percentage = (1 - word_similarity) * 100.0
            
            # Store override similarity (style similarity between latest old and new)
            segment.override_similarity_score = metrics_service.calculate_single_style_similarity(
                latest_override.new_translation,
                latest_override.old_translation if latest_override.old_translation else segment.translated_az
            )
            
            # For override segments, we need to find the ORIGINAL translation source (before ANY override)
            # This is stored in the first override's old_translation
            if original_translation_before_any_override:
                try:
                    from backend.services.style_memory import get_style_memory_service
                    style_memory_service = get_style_memory_service()
                    
                    # Check if ORIGINAL translation (before any override) matches style memory
                    nearest = style_memory_service.find_nearest(segment.source_en, k=1, threshold=0.50)
                    if nearest:
                        entry, similarity = nearest[0]
                        # Calculate how similar the ORIGINAL translation (before any override) was to style memory
                        original_style_sim = metrics_service.calculate_single_style_similarity(
                            original_translation_before_any_override,
                            entry["preferred_az"]
                        )
                        # Store this for percentage calculation
                        original_style_similarity = original_style_sim
                        if similarity >= 0.95:
                            original_from_style_memory = True
                            original_translation_source = "style_memory"
                        else:
                            original_from_style_memory = False
                            original_translation_source = "model"
                except Exception as e:
                    logger.warning(f"Error checking original translation source: {e}")
            
            logger.info(f"Segment {segment.id}: {words_changed}/{total_words} words changed in latest override ({segment.override_percentage:.1f}%), similarity: {segment.override_similarity_score:.3f}")
        except Exception as e:
            logger.warning(f"Error calculating override metrics: {e}")
            # Fallback: assume 100% override if we can't calculate
            segment.override_percentage = 100.0
            try:
                segment.override_similarity_score = metrics_service.calculate_single_style_similarity(
                    latest_override.new_translation,
                    latest_override.old_translation if latest_override.old_translation else segment.translated_az
                )
            except:
                pass
    else:
        segment.override_percentage = 0.0
    
    # For override segments, we need to preserve the original translation source info
    # so we can properly calculate the percentage breakdown
    # IMPORTANT: Check for override FIRST, because after override, a style_memory entry is created
    # which would make us think the current translation is from style_memory (wrong!)
    
    if segment.has_override:
        # For override segments, use the original translation source info we calculated earlier
        # This tells us what the ORIGINAL translation was (before override)
        # The current translation is the override, but we need to know the original source
        segment.translation_source = original_translation_source or "model"
        segment.from_style_memory = original_from_style_memory
        segment.style_similarity_score = original_style_similarity
    else:
        # Not overridden - check if translation came from style memory
        style_memory = db.query(StyleMemory).filter(
            StyleMemory.segment_id == segment.id
        ).first()
        
        if style_memory:
            segment.from_style_memory = True
            segment.translation_source = "style_memory"
            # Calculate similarity to style memory entry
            try:
                segment.style_similarity_score = metrics_service.calculate_single_style_similarity(
                    segment.translated_az,
                    style_memory.preferred_az
                )
            except Exception as e:
                logger.warning(f"Error calculating style similarity: {e}")
        else:
            # Check if similar translation exists in style memory (for model translations)
            segment.translation_source = "model"
            segment.from_style_memory = False
        
        try:
            from backend.services.style_memory import get_style_memory_service
            style_memory_service = get_style_memory_service()
            
            # Use lower threshold to find more matches (0.50 instead of 0.70)
            # This allows segments from training data to match style memory entries
            nearest = style_memory_service.find_nearest(segment.source_en, k=1, threshold=0.50)
            if nearest:
                entry, similarity = nearest[0]
                # Calculate translation similarity (how similar is the actual translation to style memory)
                translation_similarity = metrics_service.calculate_single_style_similarity(
                    segment.translated_az,
                    entry["preferred_az"]
                )
                
                # If source similarity is very high (>= 0.95), we likely used style memory
                if similarity >= 0.95:
                    segment.from_style_memory = True
                    segment.translation_source = "style_memory"
                    segment.style_similarity_score = translation_similarity  # Use translation similarity, not source similarity
                else:
                    # Source is similar but not identical - use translation similarity
                    # This shows how close the model translation is to the style memory preference
                    segment.style_similarity_score = translation_similarity
                    segment.translation_source = "model"
            else:
                # No style memory match found - try to find any style memory entry for comparison
                # This is a fallback to ensure we always have some similarity score
                try:
                    # Get any style memory entry to compare against (for baseline)
                    all_entries = style_memory_service.get_recent_overrides(limit=1)
                    if all_entries:
                        # Compare against a random style memory entry as baseline
                        baseline_entry = all_entries[0]
                        baseline_similarity = metrics_service.calculate_single_style_similarity(
                            segment.translated_az,
                            baseline_entry.get("target", "")
                        )
                        # Use a lower score since it's not a direct match
                        segment.style_similarity_score = baseline_similarity * 0.7  # Scale down since it's not a match
                    else:
                        segment.style_similarity_score = None
                except:
                    segment.style_similarity_score = None
                logger.debug(f"No style memory match for segment {segment.id}, style_similarity_score set to {segment.style_similarity_score}")
        except Exception as e:
            logger.warning(f"Error checking style memory for segment {segment.id}: {e}")
            segment.translation_source = "model"
            segment.style_similarity_score = None
    
    # Flush changes but don't commit - let the caller commit
    db.flush()


@router.get("/book/{book_id}", response_model=SegmentListResponse)
def get_book_segments(
    book_id: int,
    page: int = 1,
    page_size: int = 50,
    include_metrics: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get segments for a book with pagination."""
    skip = (page - 1) * page_size
    
    # Order by segment_index to ensure consistent ordering
    segments = db.query(Segment).filter(
        Segment.book_id == book_id
    ).order_by(Segment.segment_index.asc()).offset(skip).limit(page_size).all()
    
    total = db.query(Segment).filter(Segment.book_id == book_id).count()
    
    # Return segments with stored metrics
    segment_responses = []
    segments_to_calculate = []
    
    for segment in segments:
        # If metrics are requested but not calculated, mark for calculation
        if include_metrics and segment.translated_az and segment.style_similarity_score is None:
            segments_to_calculate.append(segment)
    
    # Calculate metrics for segments that need it
    if segments_to_calculate:
        for segment in segments_to_calculate:
            try:
                calculate_and_store_segment_metrics(segment, db)
            except Exception as e:
                logger.warning(f"Error calculating metrics for segment {segment.id}: {e}")
        db.commit()
        
        # Refresh all segments to get updated metrics
        for segment in segments:
            db.refresh(segment)
    
    for segment in segments:
        segment_responses.append(SegmentResponse.model_validate(segment))
    
    return SegmentListResponse(
        segments=segment_responses,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{segment_id}", response_model=SegmentResponse)
def get_segment(
    segment_id: int,
    include_metrics: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific segment."""
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    # If metrics are requested but not calculated, calculate them now
    if include_metrics and segment.translated_az and segment.style_similarity_score is None:
        try:
            calculate_and_store_segment_metrics(segment, db)
            db.commit()
            db.refresh(segment)
        except Exception as e:
            logger.warning(f"Error calculating metrics for segment {segment.id}: {e}")
    
    return SegmentResponse.model_validate(segment)


@router.post("/{segment_id}/override", response_model=OverrideResponse)
def override_translation(
    segment_id: int,
    request: OverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Override a segment's translation and store in style memory."""
    try:
        # Get segment
        segment = db.query(Segment).filter(Segment.id == segment_id).first()
        if not segment:
            raise HTTPException(status_code=404, detail="Segment not found")
        
        # Store old translation
        old_translation = segment.translated_az
        
        # Update segment
        segment.translated_az = request.new_translation
        segment.status = "overridden"
        segment.has_override = True
        db.flush()
        
        # Create override record
        override = Override(
            segment_id=segment_id,
            old_translation=old_translation,
            new_translation=request.new_translation,
            user_id=current_user.id,
            engine=request.engine,
            reason=request.reason
        )
        db.add(override)
        db.flush()
        
        # Add to style memory
        style_memory_service = get_style_memory_service()
        
        # Calculate similarity to original model output (if exists)
        similarity_score = None
        if old_translation:
            from backend.services.metrics import get_metrics_service
            metrics_service = get_metrics_service()
            similarity_score = metrics_service.calculate_single_style_similarity(
                request.new_translation,
                old_translation
            )
        
        style_memory_service.add_memory(
            source_en=segment.source_en,
            preferred_az=request.new_translation,
            segment_id=segment_id,
            approved_by=current_user.id,
            engine=request.engine,
            similarity_score=similarity_score
        )
        
        # IMPORTANT: Recalculate metrics AFTER all changes are made
        # This will recalculate override_percentage, style_similarity_score, etc.
        # It will use the FIRST override to find original source, and LATEST override for current percentage
        calculate_and_store_segment_metrics(segment, db)
        
        # Commit all changes
        db.commit()
        
        # Refresh to get the latest data (including updated metrics)
        db.refresh(segment)
        db.refresh(override)
        
        logger.info(f"Override successful for segment {segment_id}:")
        logger.info(f"  Old: {old_translation[:50] if old_translation else 'None'}...")
        logger.info(f"  New: {request.new_translation[:50]}...")
        logger.info(f"  Override %: {segment.override_percentage:.1f}%")
        logger.info(f"  Style similarity: {segment.style_similarity_score}")
        
        return OverrideResponse.model_validate(override)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Override error for segment {segment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Override error: {str(e)}")

