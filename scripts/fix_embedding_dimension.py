"""Fix embedding dimension in style_memory table from 768 to 384."""
import sys
from pathlib import Path
import psycopg2
import os

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import settings after adding to path
from config.settings import settings

def fix_embedding_dimension():
    """Fix the embedding dimension in the database."""
    try:
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db
        )
        cursor = conn.cursor()
        
        print("Fixing embedding dimension from 768 to 384...")
        
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM style_memory")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"Warning: Found {count} existing style_memory entries.")
            print("These will be deleted to fix the dimension mismatch.")
            response = input("Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                return
            
            # Delete existing entries
            cursor.execute("DELETE FROM style_memory")
            print(f"Deleted {count} entries.")
        
        # Drop the existing index
        print("Dropping existing index...")
        cursor.execute("DROP INDEX IF EXISTS idx_style_memory_embedding")
        
        # Alter the column
        print("Altering embedding column to 384 dimensions...")
        cursor.execute("ALTER TABLE style_memory ALTER COLUMN embedding TYPE vector(384)")
        
        # Recreate the index
        print("Recreating index...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_style_memory_embedding 
            ON style_memory USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        
        conn.commit()
        print("✓ Embedding dimension fixed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Fix Embedding Dimension")
    print("=" * 60)
    print("\nThis will change the embedding dimension from 768 to 384")
    print("to match the 'paraphrase-multilingual-MiniLM-L12-v2' model.\n")
    
    fix_embedding_dimension()
    
    print("\n" + "=" * 60)
    print("✓ Done!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run: python3 scripts/populate_style_memory.py")
    print("2. Run: python3 scripts/recalculate_all_segment_metrics.py")

