"""Retraining script triggered by cron or override count."""
import os
import sys
import logging
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.models.database import SessionLocal, TrainingRun
from backend.services.style_memory import get_style_memory_service
from ml.training.train_lora import train
from config.settings import settings
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/retrain.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def check_retrain_conditions() -> bool:
    """Check if retraining conditions are met."""
    style_memory_service = get_style_memory_service()
    override_count = style_memory_service.get_override_count()
    
    logger.info(f"Current override count: {override_count}, threshold: {settings.retrain_threshold}")
    
    return override_count >= settings.retrain_threshold


def prepare_retrain_data(output_path: str) -> tuple:
    """Prepare training data from style memory."""
    style_memory_service = get_style_memory_service()
    
    # Get recent overrides
    overrides = style_memory_service.get_recent_overrides(limit=settings.retrain_threshold)
    
    if len(overrides) < 100:  # Minimum samples
        logger.warning(f"Not enough overrides for retraining: {len(overrides)}")
        return None, None
    
    # Create JSONL files
    import json
    
    # Split into train/val (90/10)
    split_idx = int(len(overrides) * 0.9)
    train_data = overrides[:split_idx]
    val_data = overrides[split_idx:]
    
    train_path = os.path.join(output_path, "retrain_train.jsonl")
    val_path = os.path.join(output_path, "retrain_val.jsonl")
    
    os.makedirs(output_path, exist_ok=True)
    
    # Write train data
    with open(train_path, 'w', encoding='utf-8') as f:
        for idx, item in enumerate(train_data):
            entry = {
                "id": f"retrain_{idx}",
                "en": item["source"],
                "az": item["target"]
            }
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    # Write val data
    with open(val_path, 'w', encoding='utf-8') as f:
        for idx, item in enumerate(val_data):
            entry = {
                "id": f"retrain_val_{idx}",
                "en": item["source"],
                "az": item["target"]
            }
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    logger.info(f"Prepared {len(train_data)} train and {len(val_data)} val samples")
    return train_path, val_path


def retrain_model():
    """Main retraining function."""
    logger.info("Starting retraining process")
    
    # Check conditions
    if not check_retrain_conditions():
        logger.info("Retraining conditions not met, skipping")
        return
    
    # Create training run record
    db = SessionLocal()
    try:
        version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        training_run = TrainingRun(
            version=version,
            status="training",
            train_samples=0,
            validation_samples=0
        )
        db.add(training_run)
        db.commit()
        run_id = training_run.id
    except Exception as e:
        logger.error(f"Error creating training run: {e}")
        db.rollback()
        return
    finally:
        db.close()
    
    try:
        # Prepare data
        data_dir = os.path.join(settings.output_dir, "retrain_data")
        train_path, val_path = prepare_retrain_data(data_dir)
        
        if not train_path or not val_path:
            logger.error("Failed to prepare training data")
            return
        
        # Determine output directory
        model_output_dir = os.path.join(settings.output_dir, version)
        
        # Train
        logger.info("Starting model training")
        model, tokenizer, eval_results = train(
            train_data_path=train_path,
            val_data_path=val_path,
            output_dir=model_output_dir,
            model_name=settings.model_name,
            batch_size=8,
            learning_rate=2e-4,
            num_epochs=3,
            cache_dir=settings.model_cache_dir
        )
        
        # Update training run
        db = SessionLocal()
        try:
            training_run = db.query(TrainingRun).filter(TrainingRun.id == run_id).first()
            if training_run:
                training_run.status = "completed"
                training_run.model_path = model_output_dir
                training_run.train_samples = len(open(train_path).readlines())
                training_run.validation_samples = len(open(val_path).readlines())
                training_run.bleu_score = eval_results.get("eval_bleu", 0)
                training_run.completed_at = datetime.now()
                db.commit()
                logger.info("Training run updated successfully")
        except Exception as e:
            logger.error(f"Error updating training run: {e}")
            db.rollback()
        finally:
            db.close()
        
        logger.info("Retraining completed successfully")
    
    except Exception as e:
        logger.error(f"Error during retraining: {e}", exc_info=True)
        
        # Update training run status
        db = SessionLocal()
        try:
            training_run = db.query(TrainingRun).filter(TrainingRun.id == run_id).first()
            if training_run:
                training_run.status = "failed"
                training_run.notes = str(e)
                db.commit()
        except:
            pass
        finally:
            db.close()


def main():
    parser = argparse.ArgumentParser(description="Retrain translation model")
    parser.add_argument("--force", action="store_true", help="Force retraining regardless of conditions")
    
    args = parser.parse_args()
    
    if args.force:
        logger.info("Force retraining enabled")
        retrain_model()
    else:
        if check_retrain_conditions():
            retrain_model()
        else:
            logger.info("Retraining conditions not met")


if __name__ == "__main__":
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    main()

