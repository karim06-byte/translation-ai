"""Style memory API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models.database import get_db, User
from backend.api.schemas import StyleMemoryQuery, StyleMemoryResponse
from backend.api.auth import get_current_user
from backend.services.style_memory import get_style_memory_service

router = APIRouter(prefix="/api/style-memory", tags=["style-memory"])


@router.post("/nearest", response_model=StyleMemoryResponse)
def find_nearest_style_memory(
    query: StyleMemoryQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Find nearest style memory entries for a source text."""
    try:
        style_memory_service = get_style_memory_service()
        
        results = style_memory_service.find_nearest(
            query.source_en,
            k=query.k,
            threshold=0.7
        )
        
        entries = [entry for entry, _ in results]
        similarities = [sim for _, sim in results]
        
        return StyleMemoryResponse(
            entries=entries,
            similarities=similarities
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding style memory: {str(e)}")


@router.get("/override-count")
def get_override_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get count of recent overrides for retraining trigger."""
    try:
        style_memory_service = get_style_memory_service()
        count = style_memory_service.get_override_count()
        
        return {
            "override_count": count,
            "threshold": 500,  # From settings
            "ready_for_retrain": count >= 500
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting override count: {str(e)}")

