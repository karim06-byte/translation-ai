#!/bin/bash
# Script to retrain the translation model

echo "Starting model retraining..."

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set paths - use environment variables if set, otherwise defaults
TRAIN_DATA="${TRAIN_DATA:-data/processed/override_train_data.jsonl}"
VAL_DATA="${VAL_DATA:-data/processed/override_val_data.jsonl}"

# Fallback to original data if override data doesn't exist
if [ ! -f "$TRAIN_DATA" ]; then
    TRAIN_DATA="data/processed/combined_train.jsonl"
    VAL_DATA="data/processed/combined_val.jsonl"
fi

OUTPUT_DIR="outputs/nllb_finetuned_v2"
EPOCHS=3
BATCH_SIZE=2

# Check if training data exists
if [ ! -f "$TRAIN_DATA" ]; then
    echo "Error: Training data not found at $TRAIN_DATA"
    echo "Please run the data preparation pipeline first or create override training data."
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run training
echo "Training model with:"
echo "  Train data: $TRAIN_DATA"
echo "  Val data: $VAL_DATA"
echo "  Output: $OUTPUT_DIR"
echo "  Epochs: $EPOCHS"
echo ""

python3 ml/training/train_lora.py \
    --train-data "$TRAIN_DATA" \
    --val-data "$VAL_DATA" \
    --output-dir "$OUTPUT_DIR" \
    --epochs "$EPOCHS" \
    --batch-size "$BATCH_SIZE"

if [ $? -eq 0 ]; then
    echo ""
    echo "Training completed successfully!"
    echo "Model saved to: $OUTPUT_DIR"
    echo ""
    echo "Next steps:"
    echo "1. Restart the FastAPI server to load the new model"
    echo "2. Check metrics at http://localhost:3000/metrics"
else
    echo "Training failed!"
    exit 1
fi

