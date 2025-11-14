"""Populate style memory from existing segments and training data."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.models.database import SessionLocal, Segment, Override, StyleMemory
from backend.services.style_memory import get_style_memory_service
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def populate_from_overrides():
    """Populate style memory from override records."""
    db = SessionLocal()
    style_memory_service = get_style_memory_service()
    
    try:
        # Get all overrides
        overrides = db.query(Override).all()
        print(f"Found {len(overrides)} overrides")
        
        added_count = 0
        for override in overrides:
            segment = db.query(Segment).filter(Segment.id == override.segment_id).first()
            if segment:
                # Check if already in style memory
                existing = db.query(StyleMemory).filter(
                    StyleMemory.segment_id == segment.id
                ).first()
                
                if not existing:
                    try:
                        style_memory_service.add_memory(
                            source_en=segment.source_en,
                            preferred_az=override.new_translation,
                            segment_id=segment.id,
                            approved_by=override.user_id,
                            engine=override.engine
                        )
                        added_count += 1
                        if added_count % 10 == 0:
                            print(f"  Added {added_count} entries...")
                    except Exception as e:
                        logger.warning(f"Error adding style memory for segment {segment.id}: {e}")
        
        print(f"✓ Added {added_count} entries from overrides")
        return added_count
    
    finally:
        db.close()


def populate_from_training_data():
    """Populate style memory from static training data."""
    style_memory_service = get_style_memory_service()
    
    training_files = [
        "data/processed/combined_train.jsonl",
        "data/processed/combined_val.jsonl",
        "data/processed/retrain_combined_train.jsonl",
        "data/processed/retrain_combined_val.jsonl"
    ]
    
    added_count = 0
    for file_path in training_files:
        path = Path(file_path)
        if not path.exists():
            continue
        
        print(f"Processing {file_path}...")
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    data = json.loads(line)
                    source = data.get("source") or data.get("en")
                    target = data.get("target") or data.get("az")
                    
                    if source and target:
                        # Check if already exists
                        nearest = style_memory_service.find_nearest(source, k=1, threshold=0.99)
                        if not nearest:
                            style_memory_service.add_memory(
                                source_en=source,
                                preferred_az=target,
                                segment_id=None,
                                approved_by=None,
                                engine="training_data"
                            )
                            added_count += 1
                            if added_count % 50 == 0:
                                print(f"  Added {added_count} entries...")
                except Exception as e:
                    logger.warning(f"Error processing line: {e}")
    
    print(f"✓ Added {added_count} entries from training data")
    return added_count


def populate_from_good_segments():
    """Populate style memory from segments with high-quality translations."""
    db = SessionLocal()
    style_memory_service = get_style_memory_service()
    
    try:
        # Get segments with translations that haven't been overridden
        segments = db.query(Segment).filter(
            Segment.translated_az.isnot(None),
            Segment.translated_az != "",
            Segment.has_override == False
        ).limit(1000).all()  # Limit to avoid too many entries
        
        print(f"Found {len(segments)} segments with translations")
        
        added_count = 0
        for segment in segments:
            # Check if already in style memory
            existing = db.query(StyleMemory).filter(
                StyleMemory.segment_id == segment.id
            ).first()
            
            if not existing:
                try:
                    style_memory_service.add_memory(
                        source_en=segment.source_en,
                        preferred_az=segment.translated_az,
                        segment_id=segment.id,
                        approved_by=None,
                        engine="model"
                    )
                    added_count += 1
                    if added_count % 50 == 0:
                        print(f"  Added {added_count} entries...")
                except Exception as e:
                    logger.warning(f"Error adding style memory for segment {segment.id}: {e}")
        
        print(f"✓ Added {added_count} entries from good segments")
        return added_count
    
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Populating Style Memory")
    print("=" * 60)
    
    total = 0
    
    # 1. From overrides (highest priority - these are editor-approved)
    print("\n1. Populating from overrides...")
    total += populate_from_overrides()
    
    # 2. From training data (good quality parallel corpus)
    print("\n2. Populating from training data...")
    total += populate_from_training_data()
    
    # 3. From good segments (model translations that haven't been overridden)
    print("\n3. Populating from good segments...")
    total += populate_from_good_segments()
    
    print("\n" + "=" * 60)
    print(f"✓ Total entries added to style memory: {total}")
    print("=" * 60)

