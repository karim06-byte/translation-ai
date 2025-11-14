#!/bin/bash

# Cron script for scheduled retraining
# Add to crontab: 0 3 */14 * * /path/to/scripts/cron_retrain.sh

cd "$(dirname "$0")/.."
source venv/bin/activate 2>/dev/null || true
python scripts/retrain_lora.py >> logs/cron_retrain.log 2>&1

