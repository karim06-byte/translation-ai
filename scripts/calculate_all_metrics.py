"""Calculate and store metrics for all segments and training runs."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.models.database import SessionLocal, Segment, TrainingRun
from backend.api.segments import calculate_and_store_segment_metrics
from backend.services.metrics import get_metrics_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_segment_metrics():
    """Calculate metrics for all segments."""
    db = SessionLocal()
    try:
        segments = db.query(Segment).filter(
            Segment.translated_az.isnot(None),
            Segment.translated_az != ""
        ).all()
        
        print(f"Found {len(segments)} segments with translations")
        
        calculated = 0
        for idx, segment in enumerate(segments):
            try:
                calculate_and_store_segment_metrics(segment, db)
                calculated += 1
                
                if (idx + 1) % 50 == 0:
                    db.commit()
                    print(f"  Calculated metrics for {idx + 1}/{len(segments)} segments...")
            except Exception as e:
                logger.warning(f"Error calculating metrics for segment {segment.id}: {e}")
                db.rollback()
        
        db.commit()
        print(f"✓ Calculated metrics for {calculated}/{len(segments)} segments")
    
    finally:
        db.close()


def show_training_run_metrics():
    """Show metrics from training runs."""
    db = SessionLocal()
    try:
        runs = db.query(TrainingRun).order_by(TrainingRun.started_at.desc()).all()
        
        if not runs:
            print("No training runs found")
            return
        
        print("\n" + "=" * 60)
        print("Training Run Metrics")
        print("=" * 60)
        
        for run in runs:
            print(f"\nRun ID: {run.id}")
            print(f"Version: {run.version}")
            print(f"Status: {run.status}")
            print(f"Train Samples: {run.train_samples}")
            print(f"Val Samples: {run.validation_samples}")
            print(f"BLEU Score: {run.bleu_score if run.bleu_score else 'N/A'}")
            print(f"ChrF Score: {run.chrf_score if run.chrf_score else 'N/A'}")
            print(f"Style Similarity: {run.style_similarity_score if run.style_similarity_score else 'N/A'}")
            print(f"Model Path: {run.model_path if run.model_path else 'N/A'}")
            print(f"Started: {run.started_at}")
            print(f"Completed: {run.completed_at if run.completed_at else 'N/A'}")
    
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Calculate All Metrics")
    print("=" * 60)
    
    # Calculate segment metrics
    print("\n1. Calculating segment metrics...")
    calculate_segment_metrics()
    
    # Show training run metrics
    print("\n2. Training run metrics:")
    show_training_run_metrics()
    
    print("\n" + "=" * 60)
    print("✓ Done!")
    print("=" * 60)

