"""Recalculate metrics for all segments to populate style_similarity_score."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.models.database import SessionLocal, Segment
from backend.api.segments import calculate_and_store_segment_metrics
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def recalculate_all_metrics():
    """Recalculate metrics for all segments."""
    db = SessionLocal()
    try:
        segments = db.query(Segment).filter(
            Segment.translated_az.isnot(None),
            Segment.translated_az != ""
        ).all()
        
        print(f"Found {len(segments)} segments with translations")
        print("Recalculating metrics...")
        
        calculated = 0
        errors = 0
        
        for idx, segment in enumerate(segments):
            try:
                # Recalculate metrics
                calculate_and_store_segment_metrics(segment, db)
                calculated += 1
                
                if (idx + 1) % 10 == 0:
                    db.commit()
                    print(f"  Processed {idx + 1}/{len(segments)} segments...")
            except Exception as e:
                errors += 1
                logger.warning(f"Error calculating metrics for segment {segment.id}: {e}")
                db.rollback()
        
        db.commit()
        print(f"\n✓ Completed!")
        print(f"  Successfully calculated: {calculated}/{len(segments)}")
        print(f"  Errors: {errors}")
        
        # Show statistics
        segments_with_score = db.query(Segment).filter(
            Segment.style_similarity_score.isnot(None)
        ).count()
        segments_from_memory = db.query(Segment).filter(
            Segment.from_style_memory == True
        ).count()
        
        print(f"\nStatistics:")
        print(f"  Segments with style_similarity_score: {segments_with_score}/{len(segments)}")
        print(f"  Segments from_style_memory=True: {segments_from_memory}/{len(segments)}")
    
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Recalculate All Segment Metrics")
    print("=" * 60)
    print("\nThis will recalculate metrics for all segments.")
    print("Make sure style memory is populated first:")
    print("  python3 scripts/populate_style_memory.py\n")
    
    recalculate_all_metrics()
    
    print("\n" + "=" * 60)
    print("✓ Done!")
    print("=" * 60)

