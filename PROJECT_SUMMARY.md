# Project Summary: AI-Powered English→Azerbaijani Translation System

## Overview

A complete translation system for publishing houses that learns and preserves unique translation styles through fine-tuning and continuous learning from editor feedback.

## Architecture

### Components

1. **Data Preparation Pipeline** (`ml/data_prep/`)
   - PDF/DOCX/EPUB text extraction
   - Sentence alignment (simple length-based or bleualign)
   - Text cleaning and normalization
   - JSONL format conversion
   - Train/val/test splitting

2. **Model Training** (`ml/training/`)
   - NLLB-200 (1.3B) fine-tuning with LoRA
   - PEFT for efficient parameter updates
   - Checkpoint management
   - Evaluation metrics

3. **Backend API** (`backend/`)
   - FastAPI REST API
   - Authentication (JWT)
   - Book and segment management
   - Translation endpoints
   - Override mechanism
   - Style memory integration
   - Metrics calculation

4. **Style Memory System** (`backend/services/style_memory.py`)
   - PostgreSQL + pgvector for vector storage
   - Sentence transformer embeddings
   - Similarity search for style preservation
   - Automatic storage of editor-approved translations

5. **Frontend** (`frontend/`)
   - React-based web UI
   - Material-UI components
   - Book upload and management
   - Translation viewing and editing
   - Override interface with Gemini/ChatGPT
   - Metrics dashboard

6. **Retraining System** (`scripts/retrain_lora.py`)
   - Automatic retraining when 500+ overrides accumulate
   - Cron-based scheduling (every 14 days)
   - Version management
   - Training run tracking

## Key Features

### 1. Style Preservation
- Fine-tuned model learns publisher's translation style
- Style memory stores approved translations with embeddings
- Similarity search ensures consistency
- Attribution ratio metrics prove style preservation

### 2. Editor Workflow
- Upload English books (PDF/DOCX/EPUB)
- Automatic translation of segments
- Review side-by-side (EN/AZ)
- Override translations using Gemini or ChatGPT
- Overrides automatically stored for retraining

### 3. Continuous Learning
- Editor corrections feed into style memory
- Automatic retraining when threshold reached
- Model improves over time
- Version tracking for rollback

### 4. Comprehensive Metrics
- **BLEU**: Translation quality score
- **ChrF**: Character-level F-score
- **SSS**: Style Similarity Score
- **MOR**: Manual Override Rate
- **AR**: Attribution Ratio (style preservation %)

## Database Schema

- `users`: Editor accounts
- `books`: Book metadata
- `segments`: Translation segments (source + translation)
- `style_memory`: Approved translations with embeddings
- `overrides`: Override history
- `training_runs`: Model version tracking
- `metrics`: Daily metrics storage

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register user
- `POST /api/auth/login` - Login and get token

### Books
- `GET /api/books` - List books
- `POST /api/books` - Create book
- `POST /api/books/upload` - Upload book file
- `GET /api/books/{id}` - Get book details

### Translation
- `POST /api/translate` - Translate text
- `POST /api/translate/retranslate` - Retranslate with external API

### Segments
- `GET /api/segments/book/{book_id}` - Get book segments
- `GET /api/segments/{id}` - Get segment
- `POST /api/segments/{id}/override` - Override translation

### Metrics
- `GET /api/metrics/summary` - Get metrics summary
- `POST /api/metrics/calculate` - Calculate and store metrics

### Style Memory
- `POST /api/style-memory/nearest` - Find similar translations
- `GET /api/style-memory/override-count` - Get override count

## File Structure

```
Translation-AI/
├── backend/              # FastAPI backend
│   ├── api/            # API endpoints
│   ├── models/         # Database models
│   ├── services/       # Business logic
│   └── main.py         # FastAPI app
├── frontend/           # React frontend
│   ├── src/
│   │   ├── components/
│   │   └── context/
│   └── package.json
├── ml/                 # ML components
│   ├── data_prep/      # Data preparation
│   ├── training/       # Model training
│   └── inference/      # Inference utilities
├── database/           # Database schemas
├── scripts/            # Utility scripts
├── config/             # Configuration
├── requirements.txt    # Python dependencies
├── docker-compose.yml  # Docker setup
└── README.md          # Main documentation
```

## Technology Stack

### Backend
- FastAPI (Python web framework)
- SQLAlchemy (ORM)
- PostgreSQL + pgvector (vector database)
- Transformers (Hugging Face)
- PEFT/LoRA (efficient fine-tuning)
- Sentence Transformers (embeddings)

### Frontend
- React 18
- Material-UI
- Axios (HTTP client)
- React Router

### ML/AI
- NLLB-200 (1.3B) - Base translation model
- LoRA adapters for fine-tuning
- Sentence transformers for embeddings
- SacreBLEU for metrics

### External APIs
- OpenAI (ChatGPT)
- Google Gemini

## Setup and Deployment

See `SETUP.md` for detailed setup instructions.

Quick start:
1. Run `./scripts/setup.sh`
2. Configure `.env` file
3. Initialize database: `python database/init_db.py`
4. Prepare data: `python ml/data_prep/pipeline.py --input-dir data/raw --output-dir data/processed`
5. Train model: `python ml/training/train_lora.py ...`
6. Start backend: `uvicorn backend.main:app`
7. Start frontend: `cd frontend && npm start`

## Next Steps

1. **Data Collection**: Gather publisher's bilingual corpus
2. **Initial Training**: Train first model on existing translations
3. **Testing**: Test with sample books
4. **Deployment**: Deploy to production environment
5. **Monitoring**: Set up monitoring and alerting
6. **Iteration**: Collect feedback and improve

## Notes

- Model inference doesn't require GPU (CPU works, slower)
- GPU recommended for training
- Style memory uses pgvector for fast similarity search
- Retraining triggered by override count or time interval
- All editor corrections feed back into the system

## Support

For issues or questions, refer to:
- `README.md` - General documentation
- `SETUP.md` - Setup instructions
- API docs at `/docs` when backend is running

