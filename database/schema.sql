-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table (editors)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Books table
CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title_en VARCHAR(500) NOT NULL,
    title_az VARCHAR(500),
    author VARCHAR(255),
    year INTEGER,
    file_path VARCHAR(1000),
    file_type VARCHAR(50), -- 'pdf', 'docx', 'epub'
    status VARCHAR(50) DEFAULT 'uploaded', -- 'uploaded', 'processing', 'processed', 'error'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Segments table (sentences/paragraphs)
CREATE TABLE IF NOT EXISTS segments (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    segment_index INTEGER NOT NULL,
    source_en TEXT NOT NULL,
    translated_az TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'translated', 'approved', 'overridden'
    -- Metrics columns
    style_similarity_score FLOAT,
    from_style_memory BOOLEAN DEFAULT FALSE,
    has_override BOOLEAN DEFAULT FALSE,
    override_similarity_score FLOAT,
    translation_source VARCHAR(50) DEFAULT 'model', -- 'model' or 'style_memory'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(book_id, segment_index)
);

CREATE INDEX IF NOT EXISTS idx_segments_book_id ON segments(book_id);
CREATE INDEX IF NOT EXISTS idx_segments_status ON segments(status);
CREATE INDEX IF NOT EXISTS idx_segments_style_similarity ON segments(style_similarity_score);
CREATE INDEX IF NOT EXISTS idx_segments_from_style_memory ON segments(from_style_memory);

-- Style memory table (approved overrides with embeddings)
CREATE TABLE IF NOT EXISTS style_memory (
    id SERIAL PRIMARY KEY,
    segment_id INTEGER REFERENCES segments(id) ON DELETE SET NULL,
    source_en TEXT NOT NULL,
    preferred_az TEXT NOT NULL,
    embedding vector(768), -- Sentence transformer embedding dimension
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    engine VARCHAR(50), -- 'gemini', 'chatgpt', 'manual'
    similarity_score FLOAT, -- Cosine similarity to original model output
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_style_memory_embedding 
ON style_memory USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_style_memory_source ON style_memory(source_en);

-- Overrides table (history of all overrides)
CREATE TABLE IF NOT EXISTS overrides (
    id SERIAL PRIMARY KEY,
    segment_id INTEGER NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
    old_translation TEXT,
    new_translation TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    engine VARCHAR(50) NOT NULL, -- 'gemini', 'chatgpt', 'manual'
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_overrides_segment_id ON overrides(segment_id);
CREATE INDEX IF NOT EXISTS idx_overrides_user_id ON overrides(user_id);
CREATE INDEX IF NOT EXISTS idx_overrides_created_at ON overrides(created_at);

-- Training runs table (track model versions)
CREATE TABLE IF NOT EXISTS training_runs (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    model_path VARCHAR(1000),
    train_samples INTEGER,
    validation_samples INTEGER,
    bleu_score FLOAT,
    chrf_score FLOAT,
    style_similarity_score FLOAT,
    status VARCHAR(50) DEFAULT 'training', -- 'training', 'completed', 'failed'
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    notes TEXT
);

-- Metrics table (daily/weekly metrics tracking)
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    bleu_score FLOAT,
    chrf_score FLOAT,
    style_similarity_score FLOAT,
    manual_override_rate FLOAT,
    attribution_ratio FLOAT,
    total_segments INTEGER DEFAULT 0,
    overridden_segments INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date)
);

CREATE INDEX IF NOT EXISTS idx_metrics_date ON metrics(date);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_books_updated_at BEFORE UPDATE ON books
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_segments_updated_at BEFORE UPDATE ON segments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

