-- Add override_percentage column to segments table
-- This stores the percentage of the translation that was changed by override (0-100)

ALTER TABLE segments 
ADD COLUMN IF NOT EXISTS override_percentage FLOAT;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_segments_override_percentage ON segments(override_percentage);

COMMENT ON COLUMN segments.override_percentage IS 'Percentage of translation changed by override (0-100). If 0, no override. If 100, completely overridden.';

