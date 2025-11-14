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
    """Calculate and store metrics for a single segment in the database."""
    metrics_service = get_metrics_service()
    style_memory_service = get_style_memory_service()
    
    if not segment.translated_az:
        return
    
    # Check if segment has override
    override = db.query(Override).filter(
        Override.segment_id == segment.id
    ).order_by(Override.created_at.desc()).first()
    
    if override:
        segment.has_override = True
        # Calculate similarity between override and original translation
        try:
            segment.override_similarity_score = metrics_service.calculate_single_style_similarity(
                override.new_translation,
                segment.translated_az
            )
        except Exception as e:
            logger.warning(f"Error calculating override similarity: {e}")
    
    # Check if translation came from style memory
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
        # Check if similar translation exists in style memory
        # Only check if we don't have a direct style_memory entry
        segment.translation_source = "model"
        # Note: We skip the nearest search here to avoid vector dimension issues
        # The style_similarity_score will be calculated when style memory is used
    
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
    
    segments = db.query(Segment).filter(
        Segment.book_id == book_id
    ).offset(skip).limit(page_size).all()
    
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
        
        # Recalculate and store metrics for this segment
        calculate_and_store_segment_metrics(segment, db)
        
        db.refresh(override)
        return OverrideResponse.model_validate(override)
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Override error: {str(e)}")

