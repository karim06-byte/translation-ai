"""Fine-tune NLLB-200 model with LoRA."""
import os
import sys
import argparse
import logging
import warnings
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Suppress pin_memory warning for MPS (Apple Silicon)
warnings.filterwarnings("ignore", message=".*pin_memory.*MPS.*")

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq
)
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, TaskType
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_model_and_tokenizer(model_name: str, cache_dir: str = "./models"):
    """Load model and tokenizer."""
    logger.info(f"Loading model: {model_name}")
    
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        cache_dir=cache_dir,
        src_lang="eng_Latn",
        tgt_lang="aze_Latn"
    )
    
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_name,
        cache_dir=cache_dir,
        dtype=torch.float16 if torch.cuda.is_available() else torch.float32
    )
    
    return model, tokenizer


def setup_lora(model, r: int = 8, lora_alpha: int = 16, lora_dropout: float = 0.05):
    """Setup LoRA adapters."""
    logger.info("Setting up LoRA adapters")
    
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=r,
        lora_alpha=lora_alpha,
        target_modules=["q_proj", "v_proj", "k_proj", "out_proj"],
        lora_dropout=lora_dropout,
        bias="none"
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    return model


def preprocess_function(examples, tokenizer, max_length: int = 256):
    """Preprocess dataset for translation."""
    # Support both "en"/"az" and "source"/"target" column names
    if "en" in examples:
        inputs = examples["en"]
        targets = examples["az"]
    elif "source" in examples:
        inputs = examples["source"]
        targets = examples["target"]
    else:
        raise ValueError("Dataset must have either ('en', 'az') or ('source', 'target') columns")
    
    # Tokenize inputs
    model_inputs = tokenizer(
        inputs,
        max_length=max_length,
        truncation=True,
        padding="max_length"
    )
    
    # Tokenize targets (using text_target parameter)
    labels = tokenizer(
        text_target=targets,
        max_length=max_length,
        truncation=True,
        padding="max_length"
    )
    
    model_inputs["labels"] = labels["input_ids"]
    
    # Replace padding token id's of the labels by -100 so it's ignored by the loss
    model_inputs["labels"] = [
        [(l if l != tokenizer.pad_token_id else -100) for l in label]
        for label in model_inputs["labels"]
    ]
    
    return model_inputs


def compute_metrics(eval_pred, tokenizer):
    """Compute BLEU, ChrF, and Style Similarity metrics."""
    predictions, labels = eval_pred
    
    # Predictions are logits, need to get the predicted token ids
    if isinstance(predictions, tuple):
        predictions = predictions[0]
    
    # Get predicted token ids (argmax)
    predicted_ids = np.argmax(predictions, axis=-1)
    
    # Decode predictions
    decoded_preds = tokenizer.batch_decode(predicted_ids, skip_special_tokens=True)
    
    # Replace -100 in the labels as we can't decode them
    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
    
    # Calculate BLEU and ChrF
    import sacrebleu
    bleu = sacrebleu.corpus_bleu(decoded_preds, [decoded_labels])
    chrf = sacrebleu.corpus_chrf(decoded_preds, [decoded_labels])
    
    # Calculate Style Similarity Score (SSS) using embeddings
    style_similarity = 0.0
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        # Use the same embedding model as the metrics service
        embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        if decoded_preds and decoded_labels:
            pred_embeddings = embedding_model.encode(decoded_preds)
            ref_embeddings = embedding_model.encode(decoded_labels)
            
            similarities = []
            for pred_emb, ref_emb in zip(pred_embeddings, ref_embeddings):
                similarity = cosine_similarity([pred_emb], [ref_emb])[0][0]
                similarities.append(similarity)
            
            style_similarity = float(np.mean(similarities))
    except Exception as e:
        logger.warning(f"Error calculating style similarity during training: {e}")
    
    return {
        "bleu": bleu.score,
        "chrf": chrf.score,
        "style_similarity": style_similarity
    }


def train(
    train_data_path: str,
    val_data_path: str,
    output_dir: str,
    model_name: str = "facebook/nllb-200-distilled-1.3B",
    batch_size: int = 8,
    learning_rate: float = 2e-4,
    num_epochs: int = 3,
    max_length: int = 256,
    lora_r: int = 8,
    lora_alpha: int = 16,
    cache_dir: str = "./models",
    training_run_id: int = None
):
    """Main training function."""
    logger.info("Starting training")
    
    # Setup model and tokenizer
    model, tokenizer = setup_model_and_tokenizer(model_name, cache_dir)
    
    # Setup LoRA
    model = setup_lora(model, r=lora_r, lora_alpha=lora_alpha)
    
    # Load dataset
    logger.info(f"Loading dataset from {train_data_path}")
    dataset = load_dataset(
        "json",
        data_files={
            "train": train_data_path,
            "validation": val_data_path
        }
    )
    
    # Preprocess
    logger.info("Preprocessing dataset")
    tokenized_dataset = dataset.map(
        lambda x: preprocess_function(x, tokenizer, max_length),
        batched=True,
        remove_columns=dataset["train"].column_names
    )
    
    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True
    )
    
    # Training arguments
    # Disable pin_memory for MPS (Apple Silicon) to avoid warnings
    use_pin_memory = torch.cuda.is_available() and not torch.backends.mps.is_available()
    
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        num_train_epochs=num_epochs,
        eval_strategy="epoch",  # Changed from evaluation_strategy
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="bleu",
        greater_is_better=True,
        logging_dir=f"{output_dir}/logs",
        logging_steps=100,
        save_total_limit=3,
        fp16=torch.cuda.is_available(),
        dataloader_pin_memory=use_pin_memory,  # Disable for MPS
        push_to_hub=False,
        report_to="none"
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["validation"],
        data_collator=data_collator,
        tokenizer=tokenizer,
        compute_metrics=lambda eval_pred: compute_metrics(eval_pred, tokenizer)
    )
    
    # Train
    logger.info("Training started")
    trainer.train()
    
    # Save model
    logger.info(f"Saving model to {output_dir}")
    trainer.save_model()
    tokenizer.save_pretrained(output_dir)
    
    # Final evaluation
    logger.info("Running final evaluation")
    eval_results = trainer.evaluate()
    logger.info(f"Final BLEU score: {eval_results.get('eval_bleu', 0)}")
    
    # Store metrics in database if training_run_id provided
    if training_run_id:
        try:
            from backend.models.database import SessionLocal, TrainingRun
            from datetime import datetime
            
            db = SessionLocal()
            try:
                training_run = db.query(TrainingRun).filter(TrainingRun.id == training_run_id).first()
                if training_run:
                    training_run.model_path = str(output_dir)
                    training_run.bleu_score = eval_results.get('eval_bleu', 0.0)
                    training_run.chrf_score = eval_results.get('eval_chrf', 0.0)
                    training_run.style_similarity_score = eval_results.get('eval_style_similarity', 0.0)
                    training_run.status = "completed"
                    training_run.completed_at = datetime.now()
                    db.commit()
                    logger.info(f"✓ Stored metrics in TrainingRun ID {training_run_id}")
                else:
                    logger.warning(f"TrainingRun ID {training_run_id} not found")
            except Exception as e:
                db.rollback()
                logger.error(f"Error storing metrics: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Could not store metrics in database: {e}")
    
    return model, tokenizer, eval_results


def main():
    parser = argparse.ArgumentParser(description="Train NLLB-200 with LoRA")
    parser.add_argument("--train-data", required=True, help="Path to train JSONL file")
    parser.add_argument("--val-data", required=True, help="Path to validation JSONL file")
    parser.add_argument("--output-dir", required=True, help="Output directory for model")
    parser.add_argument("--model-name", default="facebook/nllb-200-distilled-1.3B",
                       help="Model name or path")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--learning-rate", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs")
    parser.add_argument("--max-length", type=int, default=256, help="Max sequence length")
    parser.add_argument("--lora-r", type=int, default=8, help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=16, help="LoRA alpha")
    parser.add_argument("--cache-dir", default="./models", help="Model cache directory")
    parser.add_argument("--training-run-id", type=int, default=None, help="Training run ID for metrics storage")
    
    args = parser.parse_args()
    
    train(
        args.train_data,
        args.val_data,
        args.output_dir,
        args.model_name,
        args.batch_size,
        args.learning_rate,
        args.epochs,
        args.max_length,
        args.lora_r,
        args.lora_alpha,
        args.cache_dir,
        args.training_run_id
    )


if __name__ == "__main__":
    main()

