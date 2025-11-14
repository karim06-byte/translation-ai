#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "=========================================="
echo "Complete Model Retraining Script"
echo "=========================================="

# Define paths
PROJECT_ROOT=$(dirname "$(dirname "$(readlink -f "$0" || realpath "$0")")")
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"

# Step 1: Prepare combined training data
echo ""
echo "Step 1: Preparing combined training data..."
python3 scripts/retrain_with_all_data.py

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to prepare training data!"
    exit 1
fi

# Get the latest training run ID and version
TRAIN_FILE="data/processed/retrain_combined_train.jsonl"
VAL_FILE="data/processed/retrain_combined_val.jsonl"

if [ ! -f "$TRAIN_FILE" ] || [ ! -f "$VAL_FILE" ]; then
    echo "ERROR: Training data files not found!"
    exit 1
fi

# Get training run ID from file (created by retrain_with_all_data.py)
RUN_ID_FILE="data/processed/latest_training_run_id.txt"
if [ -f "$RUN_ID_FILE" ]; then
    TRAINING_RUN_ID=$(cat "$RUN_ID_FILE" | tr -d '\n' | tr -d ' ')
    if [ ! -z "$TRAINING_RUN_ID" ] && [ "$TRAINING_RUN_ID" -eq "$TRAINING_RUN_ID" ] 2>/dev/null; then
        TRAINING_RUN_ARG="--training-run-id $TRAINING_RUN_ID"
        echo "Found training run ID: $TRAINING_RUN_ID"
    else
        echo "WARNING: Invalid training run ID in file, continuing without it..."
        TRAINING_RUN_ARG=""
    fi
else
    echo "WARNING: Training run ID file not found, continuing without it..."
    TRAINING_RUN_ARG=""
fi

# Step 2: Run training
echo ""
echo "Step 2: Starting model training..."
VERSION=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="outputs/nllb_finetuned_${VERSION}"

python3 ml/training/train_lora.py \
    --train-data "$TRAIN_FILE" \
    --val-data "$VAL_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --epochs 3 \
    --batch-size 2 \
    --learning-rate 2e-4 \
    --lora-r 8 \
    --lora-alpha 16 \
    --cache-dir "$PROJECT_ROOT/models" \
    $TRAINING_RUN_ARG

if [ $? -ne 0 ]; then
    echo "ERROR: Training failed!"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Training completed successfully!"
echo "=========================================="
echo "Model saved to: $OUTPUT_DIR"
if [ ! -z "$TRAINING_RUN_ID" ]; then
    echo "Metrics stored in TrainingRun ID: $TRAINING_RUN_ID"
fi
echo "=========================================="

