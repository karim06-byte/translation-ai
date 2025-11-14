"""Translation API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models.database import get_db, Segment, User
from backend.api.schemas import (
    TranslationRequest, TranslationResponse, RetranslateRequest, RetranslateResponse
)
from backend.services.translation import get_translation_service
from backend.services.style_memory import get_style_memory_service
from backend.services.external_apis import get_external_api_service
from backend.api.auth import get_current_user

router = APIRouter(prefix="/api/translate", tags=["translation"])


@router.post("", response_model=TranslationResponse)
def translate(
    request: TranslationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Translate English text to Azerbaijani."""
    try:
        translation_service = get_translation_service()
        style_memory_service = get_style_memory_service()
        
        # Get translation from model
        translated_az = translation_service.translate(request.source_en)
        
        # Check style memory for similar translations
        style_hint = None
        nearest = style_memory_service.find_nearest(request.source_en, k=1, threshold=0.8)
        if nearest:
            entry, similarity = nearest[0]
            style_hint = {
                "similar_source": entry["source_en"],
                "preferred_translation": entry["preferred_az"],
                "similarity": similarity
            }
        
        # If segment_id provided, update segment
        if request.segment_id:
            from backend.api.segments import calculate_and_store_segment_metrics
            segment = db.query(Segment).filter(Segment.id == request.segment_id).first()
            if segment:
                segment.translated_az = translated_az
                segment.status = "translated"
                segment.translation_source = "model"
                db.flush()
                # Calculate and store metrics
                calculate_and_store_segment_metrics(segment, db)
                db.commit()
        
        return TranslationResponse(
            translated_az=translated_az,
            segment_id=request.segment_id,
            style_hint=style_hint
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")


@router.post("/retranslate", response_model=RetranslateResponse)
def retranslate(
    request: RetranslateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retranslate a segment using external API (Gemini or ChatGPT)."""
    try:
        # Get segment
        segment = db.query(Segment).filter(Segment.id == request.segment_id).first()
        if not segment:
            raise HTTPException(status_code=404, detail="Segment not found")
        
        source_text = request.source_text or segment.source_en
        
        # Get external API service
        external_api = get_external_api_service()
        
        # Retranslate
        new_translation = external_api.retranslate(source_text, request.engine)
        
        return RetranslateResponse(
            new_translation=new_translation,
            engine=request.engine
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retranslation error: {str(e)}")

