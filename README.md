# AI-Powered English→Azerbaijani Translation System

A comprehensive translation system for publishing houses that learns and preserves unique translation styles through fine-tuning and continuous learning.

## Features

- **Fine-tuned Translation Model**: NLLB-200 (1.3B) fine-tuned with LoRA on publisher's bilingual corpus
- **Style Preservation**: Maintains publisher's unique linguistic style and terminology
- **Interactive Editor UI**: Web-based interface for reviewing and editing translations
- **Override Mechanism**: Editors can retranslate sections using Gemini or ChatGPT APIs
- **Continuous Learning**: Automatic retraining from editor corrections
- **Comprehensive Metrics**: BLEU, ChrF, Style Similarity Score, Attribution Ratio tracking

## Project Structure

```
Translation-AI/
├── backend/              # FastAPI backend
│   ├── api/             # API endpoints
│   ├── models/          # Database models
│   ├── services/        # Business logic
│   └── utils/           # Utilities
├── frontend/            # React frontend
├── ml/                  # ML components
│   ├── data_prep/       # Data preparation pipeline
│   ├── training/        # Model training scripts
│   └── inference/       # Inference and style memory
├── database/            # Database migrations and schemas
├── scripts/            # Utility scripts
└── config/             # Configuration files
```

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Database**
   ```bash
   # Install PostgreSQL with pgvector extension
   # Run database migrations
   alembic upgrade head
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Prepare Data**
   ```bash
   python ml/data_prep/pipeline.py --input-dir data/raw --output-dir data/processed
   ```

5. **Train Initial Model**
   ```bash
   python ml/training/train_lora.py --data-path data/processed/train.jsonl
   ```

6. **Start Backend**
   ```bash
   uvicorn backend.main:app --reload
   ```

7. **Start Frontend**
   ```bash
   cd frontend
   npm install
   npm start
   ```

## Usage

1. Upload English text through the web UI
2. Review AI-generated Azerbaijani translation
3. Select and override sections that need improvement
4. System automatically stores corrections for retraining
5. Model retrains periodically with accumulated corrections

## Metrics

The system tracks:
- **BLEU**: Translation quality score
- **ChrF**: Character-level F-score
- **SSS**: Style Similarity Score
- **MOR**: Manual Override Rate
- **AR**: Attribution Ratio (style preservation)

## License

Proprietary - Publishing House Translation System

