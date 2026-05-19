-- Add translation_direction column to books table
ALTER TABLE books ADD COLUMN IF NOT EXISTS translation_direction VARCHAR(20) DEFAULT 'en_to_az';
