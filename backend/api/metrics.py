"""Metrics API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime
from typing import Optional
import logging

from backend.models.database import get_db, Metric, Segment, Override, User
from backend.api.schemas import MetricsResponse
from backend.api.auth import get_current_user
from backend.services.metrics import get_metrics_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/summary", response_model=MetricsResponse)
def get_metrics_summary(
    target_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get metrics summary for a specific date or latest."""
    try:
        if target_date:
            metric_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            # Get latest metric
            latest = db.query(Metric).order_by(Metric.date.desc()).first()
            if latest:
                return MetricsResponse(
                    bleu=latest.bleu_score,
                    chrf=latest.chrf_score,
                    style_similarity_score=latest.style_similarity_score,
                    manual_override_rate=latest.manual_override_rate,
                    attribution_ratio=latest.attribution_ratio,
                    date=latest.date.isoformat()
                )
            else:
                # Calculate from current data
                return calculate_current_metrics(db)
        
        # Get metric for specific date
        metric = db.query(Metric).filter(Metric.date == metric_date).first()
        if metric:
            return MetricsResponse(
                bleu=metric.bleu_score,
                chrf=metric.chrf_score,
                style_similarity_score=metric.style_similarity_score,
                manual_override_rate=metric.manual_override_rate,
                attribution_ratio=metric.attribution_ratio,
                date=metric.date.isoformat()
            )
        else:
            raise HTTPException(status_code=404, detail="Metrics not found for this date")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")


def calculate_current_metrics(db: Session) -> MetricsResponse:
    """Calculate current metrics from database."""
    metrics_service = get_metrics_service()
    
    # Get total segments and overridden segments
    total_segments = db.query(Segment).count()
    overridden_segments = db.query(Segment).filter(Segment.status == "overridden").count()
    
    # Get segments with translations for evaluation
    segments = db.query(Segment).filter(
        Segment.translated_az.isnot(None),
        Segment.translated_az != ""
    ).limit(100).all()
    
    if not segments:
        # Return default metrics if no segments
        mor = metrics_service.calculate_manual_override_rate(total_segments, overridden_segments) if total_segments > 0 else 0.0
        return MetricsResponse(
            bleu=0.0,
            chrf=0.0,
            style_similarity_score=0.0,
            manual_override_rate=mor,
            attribution_ratio=0.0
        )
    
    # For BLEU/ChrF, we need to compare ORIGINAL model translations vs REFERENCE translations
    # Predictions = original model translations (before any overrides)
    # References = preferred translations (overrides if they exist, otherwise current translation)
    predictions = []
    references = []
    
    for s in segments:
        if not s.translated_az:
            continue
            
        # Check if there's an override (preferred translation)
        override = db.query(Override).filter(Override.segment_id == s.id).order_by(Override.created_at.asc()).first()  # Get FIRST override
        
        if override:
            # Segment has been overridden
            # Prediction = original model translation (stored in first override's old_translation)
            # Reference = preferred translation (latest override's new_translation)
            original_translation = override.old_translation if override.old_translation else s.translated_az
            
            # Get the latest override for the reference
            latest_override = db.query(Override).filter(Override.segment_id == s.id).order_by(Override.created_at.desc()).first()
            preferred_translation = latest_override.new_translation if latest_override else s.translated_az
            
            # Only add if they're different (otherwise BLEU/ChrF will be 100%)
            if original_translation != preferred_translation:
                predictions.append(original_translation)
                references.append(preferred_translation)
        else:
            # No override - can't calculate meaningful BLEU/ChrF
            # Skip this segment for BLEU/ChrF calculation
            # (We don't have a "ground truth" reference to compare against)
            pass
    
    # Calculate metrics only if we have valid prediction-reference pairs
    bleu = 0.0
    chrf = 0.0
    if len(predictions) > 0 and len(predictions) == len(references):
        bleu = metrics_service.calculate_bleu(predictions, references)
        chrf = metrics_service.calculate_chrf(predictions, references)
    elif len(segments) > 0:
        # If we have segments but no overrides, we can't calculate meaningful BLEU/ChrF
        # Return 0.0 to indicate no data available
        bleu = 0.0
        chrf = 0.0
    style_similarity = 0.0
    if len(predictions) == len(references):
        try:
            style_similarity = metrics_service.calculate_style_similarity(predictions, references)
        except Exception as e:
            logger.warning(f"Error calculating style similarity: {e}")
    mor = metrics_service.calculate_manual_override_rate(total_segments, overridden_segments)
    
    # Calculate Attribution Ratio (AR) - percentage of translations from style memory
    # AR = (segments from style memory / total translated segments) * 100
    from_style_memory_count = db.query(Segment).filter(
        Segment.from_style_memory == True,
        Segment.translated_az.isnot(None)
    ).count()
    total_translated = db.query(Segment).filter(
        Segment.translated_az.isnot(None),
        Segment.translated_az != ""
    ).count()
    
    attribution_ratio = 0.0
    if total_translated > 0:
        attribution_ratio = (from_style_memory_count / total_translated) * 100.0
    
    # Calculate average style similarity from stored metrics
    avg_style_similarity = 0.0
    segments_with_similarity = db.query(Segment).filter(
        Segment.style_similarity_score.isnot(None),
        Segment.translated_az.isnot(None)
    ).all()
    
    if segments_with_similarity:
        similarity_scores = [s.style_similarity_score for s in segments_with_similarity if s.style_similarity_score is not None]
        if similarity_scores:
            avg_style_similarity = sum(similarity_scores) / len(similarity_scores)
    
    # Use average style similarity if calculated, otherwise use the batch calculation
    if avg_style_similarity > 0:
        style_similarity = avg_style_similarity
    
    return MetricsResponse(
        bleu=bleu if bleu else 0.0,
        chrf=chrf if chrf else 0.0,
        style_similarity_score=style_similarity if style_similarity else 0.0,
        manual_override_rate=mor if mor else 0.0,
        attribution_ratio=attribution_ratio if attribution_ratio else 0.0
    )


@router.post("/calculate")
def calculate_and_store_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate and store metrics for today."""
    try:
        today = date.today()
        
        # Check if metric already exists
        existing = db.query(Metric).filter(Metric.date == today).first()
        if existing:
            raise HTTPException(status_code=400, detail="Metrics already calculated for today")
        
        # Calculate metrics
        metrics = calculate_current_metrics(db)
        
        # Store in database
        metric = Metric(
            date=today,
            bleu_score=metrics.bleu,
            chrf_score=metrics.chrf,
            style_similarity_score=metrics.style_similarity_score,
            manual_override_rate=metrics.manual_override_rate,
            attribution_ratio=metrics.attribution_ratio
        )
        db.add(metric)
        db.commit()
        
        return {"message": "Metrics calculated and stored", "date": today.isoformat()}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error calculating metrics: {str(e)}")


@router.post("/retrain")
def trigger_retraining(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger model retraining with current override data."""
    import subprocess
    import os
    from pathlib import Path
    
    try:
        # Count available data
        segment_count = db.query(Segment).filter(
            Segment.translated_az.isnot(None),
            Segment.translated_az != ""
        ).count()
        override_count = db.query(Override).count()
        
        # Check if we have any data
        if segment_count == 0:
            return {
                "message": "No translated segments found. Please translate some segments first.",
                "segment_count": segment_count,
                "override_count": override_count,
                "can_retrain": False
            }
        
        # Get script path - use the complete retraining script
        script_path = Path(__file__).parent.parent.parent / "scripts" / "retrain_model_complete.sh"
        
        if not script_path.exists():
            raise HTTPException(status_code=500, detail="Retraining script not found")
        
        # Run retraining in background
        # Note: In production, use Celery or similar task queue
        process = subprocess.Popen(
            ["bash", str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(script_path.parent.parent)
        )
        
        return {
            "message": "Retraining started in background. This will use both static training data and all database segments.",
            "process_id": process.pid,
            "segment_count": segment_count,
            "override_count": override_count,
            "can_retrain": True,
            "note": "Check terminal for progress. Metrics will be stored in TrainingRun table after completion.",
            "tip": "After training, run 'python3 scripts/populate_style_memory.py' to populate style memory from training data."
        }
    
    except Exception as e:
        logger.error(f"Error starting retraining: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error starting retraining: {str(e)}")

