"""Manually translate pending segments."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.models.database import SessionLocal, Segment, Book
from backend.services.translation import get_translation_service

def translate_pending_segments(book_id=None, limit=10):
    """Translate pending segments."""
    db = SessionLocal()
    try:
        # Get pending segments
        query = db.query(Segment).filter(Segment.status == "pending")
        if book_id:
            query = query.filter(Segment.book_id == book_id)
        
        segments = query.limit(limit).all()
        
        if not segments:
            print("No pending segments found")
            return
        
        print(f"Found {len(segments)} pending segments")
        
        # Load translation service
        print("Loading translation service...")
        translation_service = get_translation_service()
        print("Translation service loaded!")
        
        # Translate segments
        translated = 0
        for idx, segment in enumerate(segments):
            try:
                print(f"\n[{idx+1}/{len(segments)}] Translating segment {segment.id}...")
                print(f"  Source: {segment.source_en[:100]}...")
                
                translated_az = translation_service.translate(segment.source_en)
                segment.translated_az = translated_az
                segment.status = "translated"
                translated += 1
                
                print(f"  ✓ Translated: {translated_az[:100]}...")
                
                # Commit every 5 segments
                if (idx + 1) % 5 == 0:
                    db.commit()
                    print(f"  Committed {idx+1} segments")
            except Exception as e:
                print(f"  ✗ Error: {e}")
                segment.status = "error"
        
        db.commit()
        print(f"\n✓ Completed! Translated {translated}/{len(segments)} segments")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-id", type=int, help="Book ID to translate")
    parser.add_argument("--limit", type=int, default=10, help="Number of segments to translate")
    args = parser.parse_args()
    
    translate_pending_segments(args.book_id, args.limit)

