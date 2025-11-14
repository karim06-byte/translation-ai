"""Retrain model using both static training data and database segments."""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.models.database import SessionLocal, Override, Segment, TrainingRun
from config.settings import settings

def prepare_combined_training_data():
    """Prepare training data from both static files and database segments."""
    db = SessionLocal()
    training_data = []
    
    try:
        # 1. Load static training data if exists
        static_train_file = Path("data/processed/combined_train.jsonl")
        static_val_file = Path("data/processed/combined_val.jsonl")
        
        static_count = 0
        if static_train_file.exists():
            print(f"Loading static training data from {static_train_file}...")
            with open(static_train_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        # Convert to standard format
                        if "source" in data and "target" in data:
                            training_data.append({
                                "source": data["source"],
                                "target": data["target"]
                            })
                            static_count += 1
            print(f"  Loaded {static_count} examples from static data")
        
        # 2. Get all segments with translations from database
        print("Loading segments from database...")
        segments = db.query(Segment).filter(
            Segment.translated_az.isnot(None),
            Segment.translated_az != ""
        ).all()
        
        segment_count = 0
        for segment in segments:
            # Check if there's an override (preferred translation)
            override = db.query(Override).filter(
                Override.segment_id == segment.id
            ).order_by(Override.created_at.desc()).first()
            
            if override:
                # Use override as preferred translation
                training_data.append({
                    "source": segment.source_en,
                    "target": override.new_translation
                })
                segment_count += 1
            elif segment.translated_az:
                # Use the model translation
                training_data.append({
                    "source": segment.source_en,
                    "target": segment.translated_az
                })
                segment_count += 1
        
        print(f"  Loaded {segment_count} examples from database segments")
        print(f"  Total training examples: {len(training_data)}")
        
        if len(training_data) == 0:
            print("ERROR: No training data available!")
            return None, None, None
        
        # 3. Shuffle and split into train/val (80/20)
        import random
        random.shuffle(training_data)
        
        val_size = max(1, len(training_data) // 5)  # At least 1 for validation
        val_data = training_data[:val_size]
        train_data = training_data[val_size:]
        
        # 4. Save to files
        output_dir = Path("data/processed")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        train_file = output_dir / "retrain_combined_train.jsonl"
        val_file = output_dir / "retrain_combined_val.jsonl"
        
        print(f"\nSaving training data...")
        with open(train_file, 'w', encoding='utf-8') as f:
            for item in train_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        with open(val_file, 'w', encoding='utf-8') as f:
            for item in val_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"  Train: {train_file} ({len(train_data)} examples)")
        print(f"  Val: {val_file} ({len(val_data)} examples)")
        
        return str(train_file), str(val_file), len(training_data)
    
    finally:
        db.close()


def create_training_run_record(version: str, train_samples: int, val_samples: int):
    """Create a training run record in the database."""
    db = SessionLocal()
    try:
        training_run = TrainingRun(
            version=version,
            train_samples=train_samples,
            validation_samples=val_samples,
            status="training",
            started_at=datetime.now()
        )
        db.add(training_run)
        db.commit()
        db.refresh(training_run)
        return training_run.id
    except Exception as e:
        db.rollback()
        print(f"Error creating training run record: {e}")
        return None
    finally:
        db.close()


def update_training_run_metrics(
    run_id: int,
    model_path: str,
    bleu_score: float = None,
    chrf_score: float = None,
    style_similarity_score: float = None,
    status: str = "completed"
):
    """Update training run with metrics after training."""
    db = SessionLocal()
    try:
        training_run = db.query(TrainingRun).filter(TrainingRun.id == run_id).first()
        if training_run:
            training_run.model_path = model_path
            training_run.bleu_score = bleu_score
            training_run.chrf_score = chrf_score
            training_run.style_similarity_score = style_similarity_score
            training_run.status = status
            training_run.completed_at = datetime.now()
            db.commit()
            print(f"✓ Updated training run {run_id} with metrics")
        else:
            print(f"Warning: Training run {run_id} not found")
    except Exception as e:
        db.rollback()
        print(f"Error updating training run: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Preparing Combined Training Data")
    print("=" * 60)
    
    train_file, val_file, total_samples = prepare_combined_training_data()
    
    if not train_file:
        print("\nERROR: Failed to prepare training data!")
        sys.exit(1)
    
    # Create training run record
    version = f"nllb_finetuned_v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_id = create_training_run_record(
        version=version,
        train_samples=int(total_samples * 0.8),
        val_samples=int(total_samples * 0.2)
    )
    
    if run_id:
        print(f"\n✓ Training run created: ID={run_id}, Version={version}")
        # Write run_id to a file so the shell script can read it
        run_id_file = Path("data/processed/latest_training_run_id.txt")
        run_id_file.parent.mkdir(parents=True, exist_ok=True)
        with open(run_id_file, 'w') as f:
            f.write(str(run_id))
        print(f"  Run ID saved to: {run_id_file}")
    else:
        print(f"\n⚠ Warning: Could not create training run record")
        print(f"  Training will continue without metrics storage")
    
    print(f"\nNext steps:")
    print(f"1. Run training:")
    print(f"   python3 ml/training/train_lora.py \\")
    print(f"       --train-data {train_file} \\")
    print(f"       --val-data {val_file} \\")
    print(f"       --output-dir outputs/{version} \\")
    print(f"       --epochs 3 \\")
    if run_id:
        print(f"       --training-run-id {run_id}")
    print(f"\n2. After training, metrics will be stored in TrainingRun ID {run_id if run_id else 'N/A'}")

