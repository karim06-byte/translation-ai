# Setup Guide

## Prerequisites

- Python 3.10+
- PostgreSQL 15+ with pgvector extension
- Node.js 18+ (for frontend)
- Redis (optional, for Celery)

## Quick Start

### 1. Clone and Setup

```bash
# Run setup script
./scripts/setup.sh

# Or manually:
mkdir -p models outputs data/raw data/processed uploads logs
cp .env.example .env
# Edit .env with your configuration
```

### 2. Install Dependencies

```bash
# Python
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 3. Database Setup

#### Option A: Using Docker Compose

```bash
docker-compose up -d db
python database/init_db.py
```

#### Option B: Manual PostgreSQL Setup

```bash
# Install PostgreSQL with pgvector
# Create database
createdb translation_db

# Run schema
psql translation_db < database/schema.sql
```

### 4. Configure Environment

Edit `.env` file:
- Set database credentials
- Add OpenAI API key (for ChatGPT retranslation)
- Add Gemini API key (for Gemini retranslation)
- Set secret key for JWT tokens

### 5. Prepare Training Data

```bash
# Place your English and Azerbaijani book pairs in data/raw/
# Format: book1_en.pdf, book1_az.pdf, etc.

python ml/data_prep/pipeline.py \
  --input-dir data/raw \
  --output-dir data/processed \
  --alignment simple
```

### 6. Train Initial Model

```bash
python ml/training/train_lora.py \
  --train-data data/processed/combined_train.jsonl \
  --val-data data/processed/combined_val.jsonl \
  --output-dir outputs/nllb_finetuned_v1
```

### 7. Start Services

#### Backend

```bash
uvicorn backend.main:app --reload
```

#### Frontend

```bash
cd frontend
npm start
```

#### Using Docker Compose

```bash
docker-compose up
```

### 8. Setup Retraining Cron Job

```bash
# Edit crontab
crontab -e

# Add line (runs every 14 days at 3 AM)
0 3 */14 * * /path/to/Translation-AI/scripts/cron_retrain.sh
```

## Usage

1. **Login**: Access http://localhost:3000 and login
2. **Upload Book**: Upload English book file (PDF/DOCX/EPUB)
3. **Translate**: System automatically translates segments
4. **Review**: Review translations in the book view
5. **Override**: Select segments and override with Gemini/ChatGPT
6. **Metrics**: View translation quality metrics

## API Documentation

Once backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### Database Connection Issues

- Ensure PostgreSQL is running
- Check `.env` database credentials
- Verify pgvector extension: `psql -c "CREATE EXTENSION vector;"`

### Model Loading Issues

- Ensure model files are in `outputs/` directory
- Check model path in settings
- Verify Hugging Face cache directory

### Frontend Connection Issues

- Check API URL in frontend `.env` or `package.json` proxy
- Ensure backend is running on port 8000
- Check CORS settings in `backend/main.py`

## Production Deployment

1. Set `DEBUG=False` in `.env`
2. Use production database
3. Configure proper CORS origins
4. Use reverse proxy (nginx)
5. Enable HTTPS
6. Set up proper logging and monitoring

