"""Retrain model using override data from database."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.models.database import SessionLocal, Override, Segment
import json

def prepare_training_data_from_overrides():
    """Prepare training data from override records."""
    db = SessionLocal()
    try:
        # Get all overrides (these are the preferred translations)
        overrides = db.query(Override).all()
        
        if not overrides:
            print("No overrides found in database. Need at least some overrides to retrain.")
            return None
        
        print(f"Found {len(overrides)} overrides")
        
        # Create training data
        training_data = []
        for override in overrides:
            segment = db.query(Segment).filter(Segment.id == override.segment_id).first()
            if segment:
                training_data.append({
                    "source": segment.source_en,
                    "target": override.new_translation  # Use the override as preferred translation
                })
        
        print(f"Prepared {len(training_data)} training examples")
        
        # Save to JSONL file
        output_file = Path("data/processed/override_training_data.jsonl")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in training_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"Saved training data to {output_file}")
        return str(output_file)
    
    finally:
        db.close()

if __name__ == "__main__":
    data_file = prepare_training_data_from_overrides()
    if data_file:
        print(f"\nTraining data prepared: {data_file}")
        print("You can now run:")
        print(f"python3 ml/training/train_lora.py --train-data {data_file} --val-data data/processed/combined_val.jsonl --output-dir outputs/nllb_finetuned_v2 --epochs 3")

