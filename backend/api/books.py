"""Books API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
import sys
import shutil
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.models.database import get_db, Book, Segment, User
from backend.api.schemas import BookCreate, BookResponse
from backend.api.auth import get_current_user
from ml.data_prep.extractors import extract_text
from ml.data_prep.cleaning import clean_text, sentence_tokenize
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/books", tags=["books"])


def translate_book_segments(book_id: int):
    """Background task to translate all segments of a book."""
    import sys
    print(f"\n{'='*60}", file=sys.stderr, flush=True)
    print(f"[TRANSLATION TASK] Starting translation for book {book_id}", file=sys.stderr, flush=True)
    print(f"{'='*60}\n", file=sys.stderr, flush=True)
    
    from backend.models.database import SessionLocal
    from backend.services.translation import get_translation_service
    
    db = SessionLocal()
    try:
        # Get all pending segments for this book
        segments = db.query(Segment).filter(
            Segment.book_id == book_id,
            Segment.status == "pending"
        ).all()
        
        if not segments:
            print(f"[TRANSLATION TASK] No pending segments for book {book_id}", file=sys.stderr, flush=True)
            logger.info(f"No pending segments for book {book_id}")
            return
        
        print(f"[TRANSLATION TASK] Found {len(segments)} segments to translate", file=sys.stderr, flush=True)
        logger.info(f"Translating {len(segments)} segments for book {book_id}")
        
        # Initialize translation service
        print(f"[TRANSLATION TASK] Loading translation service...", file=sys.stderr, flush=True)
        try:
            translation_service = get_translation_service()
            print(f"[TRANSLATION TASK] ✓ Translation service loaded successfully", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[TRANSLATION TASK] ✗ ERROR loading translation service: {e}", file=sys.stderr, flush=True)
            logger.error(f"Error loading translation service: {e}", exc_info=True)
            raise
        
        # Translate each segment
        from backend.api.segments import calculate_and_store_segment_metrics
        
        translated_count = 0
        error_count = 0
        for idx, segment in enumerate(segments):
            try:
                print(f"[TRANSLATION TASK] [{idx+1}/{len(segments)}] Translating segment {segment.id}...", file=sys.stderr, flush=True)
                print(f"  Source: {segment.source_en[:80]}...", file=sys.stderr, flush=True)
                
                # Translate with style memory integration
                translated_az = translation_service.translate(segment.source_en, use_style_memory=True)
                
                segment.translated_az = translated_az
                segment.status = "translated"
                segment.translation_source = "model"  # Will be updated by calculate_and_store_segment_metrics
                db.flush()
                
                # Calculate and store metrics (this will check style memory and update translation_source)
                try:
                    calculate_and_store_segment_metrics(segment, db)
                except Exception as e:
                    logger.warning(f"Error calculating metrics for segment {segment.id}: {e}")
                
                translated_count += 1
                
                print(f"  ✓ Translated: {translated_az[:80]}...", file=sys.stderr, flush=True)
                logger.info(f"Translated segment {segment.id}")
                
                # Commit every 10 segments to save progress
                if (idx + 1) % 10 == 0:
                    db.commit()
                    print(f"[TRANSLATION TASK] Progress: {idx+1}/{len(segments)} segments translated (committed)", file=sys.stderr, flush=True)
            except Exception as e:
                error_count += 1
                print(f"  ✗ ERROR: {str(e)[:100]}", file=sys.stderr, flush=True)
                logger.error(f"Error translating segment {segment.id}: {e}", exc_info=True)
                segment.status = "error"
        
        db.commit()
        print(f"\n{'='*60}", file=sys.stderr, flush=True)
        print(f"[TRANSLATION TASK] ✓ COMPLETED!", file=sys.stderr, flush=True)
        print(f"  Book ID: {book_id}", file=sys.stderr, flush=True)
        print(f"  Translated: {translated_count}/{len(segments)}", file=sys.stderr, flush=True)
        print(f"  Errors: {error_count}", file=sys.stderr, flush=True)
        print(f"{'='*60}\n", file=sys.stderr, flush=True)
        logger.info(f"Completed translation for book {book_id}: {translated_count}/{len(segments)} segments")
    
    except Exception as e:
        print(f"\n[TRANSLATION TASK] ✗ FATAL ERROR: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        logger.error(f"Error in translate_book_segments: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
        print(f"[TRANSLATION TASK] Task finished for book {book_id}\n", file=sys.stderr, flush=True)


@router.post("", response_model=BookResponse)
def create_book(
    book_data: BookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new book entry."""
    book = Book(
        title_en=book_data.title_en,
        title_az=book_data.title_az,
        author=book_data.author,
        year=book_data.year,
        status="uploaded"
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.post("/upload")
def upload_book(
    file: UploadFile = File(...),
    book_id: int = None,
    auto_translate: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a book file and extract segments."""
    try:
        print(f"\n[UPLOAD] Starting upload: {file.filename}", flush=True)
        
        # Create uploads directory
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        # Save file
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"[UPLOAD] File saved to: {file_path}", flush=True)
        
        # Extract text
        from ml.data_prep.extractors import extract_text
        text = extract_text(str(file_path))
        if not text:
            raise HTTPException(status_code=400, detail="Failed to extract text from file")
        
        print(f"[UPLOAD] Extracted {len(text)} characters", flush=True)
        
        # Clean and tokenize
        text = clean_text(text)
        
        # Improved sentence tokenization - ensure proper sentence splitting
        sentences = sentence_tokenize(text, language='en')
        
        # Filter and validate sentences
        valid_sentences = []
        for sent in sentences:
            sent = sent.strip()
            # Only include sentences that are:
            # - At least 10 characters (not just punctuation)
            # - Not just whitespace
            # - Have actual content (not just numbers/symbols)
            if len(sent) >= 10 and sent and not sent.isspace():
                # Check if it has at least one letter
                if any(c.isalpha() for c in sent):
                    valid_sentences.append(sent)
        
        sentences = valid_sentences
        print(f"[UPLOAD] Tokenized into {len(sentences)} valid sentences", flush=True)
        
        # Create or get book
        if book_id:
            book = db.query(Book).filter(Book.id == book_id).first()
            if not book:
                raise HTTPException(status_code=404, detail="Book not found")
        else:
            book = Book(
                title_en=file.filename,
                file_path=str(file_path),
                file_type=file.filename.split('.')[-1],
                status="processing"
            )
            db.add(book)
            db.commit()
            db.refresh(book)
        
        # Create segments
        print(f"[UPLOAD] Creating {len(sentences)} segments...", flush=True)
        for idx, sentence in enumerate(sentences):
            segment = Segment(
                book_id=book.id,
                segment_index=idx,
                source_en=sentence,
                status="pending"
            )
            db.add(segment)
        
        book.status = "processed"
        db.commit()
        
        print(f"[UPLOAD] ✓ Book {book.id} created with {len(sentences)} segments", flush=True)
        logger.info(f"Book {book.id} uploaded with {len(sentences)} segments")
        
        message = f"Book uploaded with {len(sentences)} segments."
        
        # Start background translation task if enabled
        if auto_translate:
            print(f"[UPLOAD] Starting background translation task...", flush=True)
            logger.info(f"Starting translation for book {book.id}")
            background_tasks.add_task(translate_book_segments, book.id)
            print(f"[UPLOAD] ✓ Background task added for book {book.id}", flush=True)
            message += " Translation started in background. Check terminal for progress."
        else:
            message += " Use 'Translate All Pending' button to start translation."
        
        from fastapi.responses import JSONResponse
        
        response_data = {
            "book_id": book.id,
            "segments_created": len(sentences),
            "status": "success",
            "message": message
        }
        
        # Return response with background tasks
        if auto_translate:
            return JSONResponse(content=response_data, background=background_tasks)
        else:
            return response_data
    
    except Exception as e:
        print(f"[UPLOAD] ✗ ERROR: {e}", flush=True)
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")


@router.post("/{book_id}/translate-all")
def translate_all_segments(
    book_id: int,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    sync: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger translation for all pending segments of a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    from fastapi.responses import JSONResponse
    
    if sync:
        # Run synchronously (for testing/debugging)
        print(f"[SYNC TRANSLATION] Starting synchronous translation for book {book_id}", flush=True)
        translate_book_segments(book_id)
        return {
            "book_id": book_id,
            "status": "completed",
            "message": "Translation completed synchronously. Check terminal for details."
        }
    else:
        # Start background translation
        print(f"[ASYNC TRANSLATION] Adding background task for book {book_id}", flush=True)
        background_tasks.add_task(translate_book_segments, book_id)
        response_data = {
            "book_id": book_id,
            "status": "started",
            "message": "Translation started in background. Check terminal for progress."
        }
        return JSONResponse(content=response_data, background=background_tasks)


@router.get("", response_model=List[BookResponse])
def list_books(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all books."""
    books = db.query(Book).offset(skip).limit(limit).all()
    return books


@router.get("/{book_id}", response_model=BookResponse)
def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book
