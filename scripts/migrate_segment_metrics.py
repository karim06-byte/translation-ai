"""Migration script to add metrics columns to segments table and calculate metrics for existing segments."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
from config.settings import settings
from backend.models.database import SessionLocal, Segment
from backend.api.segments import calculate_and_store_segment_metrics

def run_migration():
    """Run migration to add metrics columns and calculate metrics."""
    print("Starting migration...")
    
    # Connect to database
    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db
    )
    cursor = conn.cursor()
    
    try:
        # Add columns if they don't exist
        print("Adding metrics columns to segments table...")
        cursor.execute("""
            ALTER TABLE segments 
            ADD COLUMN IF NOT EXISTS style_similarity_score FLOAT,
            ADD COLUMN IF NOT EXISTS from_style_memory BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS has_override BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS override_similarity_score FLOAT,
            ADD COLUMN IF NOT EXISTS translation_source VARCHAR(50) DEFAULT 'model';
        """)
        
        # Create indexes
        print("Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_segments_style_similarity 
            ON segments(style_similarity_score);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_segments_from_style_memory 
            ON segments(from_style_memory);
        """)
        
        conn.commit()
        print("✓ Migration completed successfully!")
        
        # Calculate metrics for existing segments
        print("\nCalculating metrics for existing segments...")
        db = SessionLocal()
        try:
            segments = db.query(Segment).filter(
                Segment.translated_az.isnot(None),
                Segment.translated_az != ""
            ).all()
            
            print(f"Found {len(segments)} segments with translations")
            
            for idx, segment in enumerate(segments):
                if (idx + 1) % 10 == 0:
                    print(f"Processing segment {idx+1}/{len(segments)}...")
                    db.commit()  # Commit every 10 segments
                
                try:
                    calculate_and_store_segment_metrics(segment, db)
                    # Commit after each calculation to ensure it's saved
                    db.commit()
                except Exception as e:
                    print(f"Error calculating metrics for segment {segment.id}: {e}")
                    db.rollback()
            
            # Final commit
            db.commit()
            print(f"✓ Calculated metrics for {len(segments)} segments")
        
        except Exception as e:
            db.rollback()
            print(f"Error calculating metrics: {e}")
        finally:
            db.close()
    
    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()

