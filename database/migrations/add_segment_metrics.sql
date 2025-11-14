-- Migration: Add metrics columns to segments table
-- Run this migration to add metrics storage to segments

ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS style_similarity_score FLOAT,
ADD COLUMN IF NOT EXISTS from_style_memory BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS has_override BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS override_similarity_score FLOAT,
ADD COLUMN IF NOT EXISTS translation_source VARCHAR(50) DEFAULT 'model'; -- 'model' or 'style_memory'

CREATE INDEX IF NOT EXISTS idx_segments_style_similarity ON segments(style_similarity_score);
CREATE INDEX IF NOT EXISTS idx_segments_from_style_memory ON segments(from_style_memory);

