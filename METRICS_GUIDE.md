# Metrics System Guide

## Overview

The translation system now stores metrics directly in the `segments` table for each translated segment. This allows you to see quality metrics for each translation in real-time.

## Database Schema

The `segments` table now includes these metrics columns:

- **`style_similarity_score`** (FLOAT): Similarity score (0-1) to style memory entries
- **`from_style_memory`** (BOOLEAN): Whether translation came from style memory
- **`has_override`** (BOOLEAN): Whether segment was manually overridden
- **`override_similarity_score`** (FLOAT): Similarity between override and original translation
- **`translation_source`** (VARCHAR): 'model' or 'style_memory'

## How Metrics Are Calculated

### Automatic Calculation

Metrics are automatically calculated and stored when:
1. A segment is translated (via API or background task)
2. A segment is overridden by an editor
3. A segment is viewed (if metrics haven't been calculated yet)

### Metrics Calculation Process

1. **Style Similarity Score**: Calculated using cosine similarity between:
   - The segment's translation
   - The preferred translation from style memory (if exists)

2. **Translation Source**: 
   - `'model'`: Translation from AI model
   - `'style_memory'`: Translation retrieved from style memory

3. **Override Similarity**: 
   - Calculated when a segment is overridden
   - Compares the new override translation with the original model translation

## Viewing Metrics

### In the UI

1. Open any book with translated segments
2. Each segment shows a **"Translation Metrics"** box with:
   - **Style Similarity**: Percentage similarity to style memory
   - **Source**: "AI Model" (blue) or "Style Memory" (green)
   - **Override Similarity**: If the segment was overridden

### Via API

```bash
# Get segments with metrics
GET /api/segments/book/{book_id}?include_metrics=true

# Response includes:
{
  "segments": [
    {
      "id": 1,
      "source_en": "Hello world",
      "translated_az": "Salam dünya",
      "style_similarity_score": 0.85,
      "from_style_memory": false,
      "translation_source": "model",
      "has_override": false
    }
  ]
}
```

## Retraining the Model

### When to Retrain

- After collecting 500+ overrides (configurable threshold)
- When you want to improve model quality with editor corrections
- Periodically (e.g., every 2 weeks)

### How to Retrain

#### Option 1: Via UI
1. Go to Metrics Dashboard
2. Click "Retrain Model" button
3. System will:
   - Check if you have enough overrides (500+)
   - Prepare training data from overrides
   - Start training in background

#### Option 2: Via Script
```bash
# Prepare training data from overrides
python3 scripts/retrain_with_overrides.py

# Run training
bash scripts/retrain_model.sh
```

#### Option 3: Manual Training
```bash
python3 ml/training/train_lora.py \
    --train-data data/processed/override_train_data.jsonl \
    --val-data data/processed/override_val_data.jsonl \
    --output-dir outputs/nllb_finetuned_v2 \
    --epochs 3 \
    --batch-size 2
```

## Migration

If you have existing segments without metrics, run:

```bash
python3 scripts/migrate_segment_metrics.py
```

This will:
1. Add metrics columns to segments table (if not exists)
2. Calculate metrics for all existing translated segments
3. Store metrics in the database

## Metrics Dashboard

The Metrics Dashboard (`/metrics`) shows:
- **BLEU Score**: Translation quality metric
- **ChrF Score**: Character-level F-score
- **Style Similarity**: Average style similarity across segments
- **Override Rate**: Percentage of segments that were overridden
- **Attribution Ratio**: Percentage of translations from style memory

## Troubleshooting

### Metrics Not Showing

1. Run migration: `python3 scripts/migrate_segment_metrics.py`
2. Refresh the book view
3. Metrics will be calculated automatically when you view segments

### Metrics Not Calculating

- Check if segments have translations
- Check logs for errors in metrics calculation
- Ensure sentence-transformers model is loaded

### Retraining Not Starting

- Check if you have enough overrides (500+)
- Check terminal for error messages
- Verify training data files exist

