-- Fix embedding dimension from 768 to 384
-- The model 'paraphrase-multilingual-MiniLM-L12-v2' produces 384-dimensional embeddings

-- Drop the existing index
DROP INDEX IF EXISTS idx_style_memory_embedding;

-- Alter the column to use 384 dimensions
-- Note: This will fail if there's existing data with 768 dimensions
-- If you have existing data, you'll need to drop and recreate the table
ALTER TABLE style_memory 
ALTER COLUMN embedding TYPE vector(384);

-- Recreate the index
CREATE INDEX IF NOT EXISTS idx_style_memory_embedding 
ON style_memory USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

