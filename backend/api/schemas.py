"""Pydantic schemas for API requests and responses."""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# Authentication
class Token(BaseModel):
    access_token: str
    token_type: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


# Books
class BookCreate(BaseModel):
    title_en: str
    title_az: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None


class BookResponse(BaseModel):
    id: int
    title_en: str
    title_az: Optional[str]
    author: Optional[str]
    year: Optional[int]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Segments
class SegmentMetrics(BaseModel):
    """Metrics for a single segment."""
    style_similarity: Optional[float] = None
    has_override: bool = False
    override_similarity: Optional[float] = None
    from_style_memory: bool = False
    translation_source: Optional[str] = None
    
    class Config:
        from_attributes = True


class SegmentResponse(BaseModel):
    id: int
    book_id: int
    segment_index: int
    source_en: str
    translated_az: Optional[str]
    status: str
    # Metrics fields
    style_similarity_score: Optional[float] = None
    from_style_memory: bool = False
    has_override: bool = False
    override_similarity_score: Optional[float] = None
    translation_source: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SegmentListResponse(BaseModel):
    segments: List[SegmentResponse]
    total: int
    page: int
    page_size: int


# Translation
class TranslationRequest(BaseModel):
    source_en: str
    segment_id: Optional[int] = None


class TranslationResponse(BaseModel):
    translated_az: str
    segment_id: Optional[int] = None
    style_hint: Optional[dict] = None


class RetranslateRequest(BaseModel):
    segment_id: int
    engine: str  # 'gemini' or 'chatgpt'
    source_text: Optional[str] = None


class RetranslateResponse(BaseModel):
    new_translation: str
    engine: str


# Override
class OverrideRequest(BaseModel):
    segment_id: int
    new_translation: str
    engine: str
    reason: Optional[str] = None


class OverrideResponse(BaseModel):
    id: int
    segment_id: int
    old_translation: Optional[str]
    new_translation: str
    engine: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Style Memory
class StyleMemoryQuery(BaseModel):
    source_en: str
    k: int = 5


class StyleMemoryResponse(BaseModel):
    entries: List[dict]
    similarities: List[float]


# Metrics
class MetricsResponse(BaseModel):
    bleu: Optional[float] = None
    chrf: Optional[float] = None
    style_similarity_score: Optional[float] = None
    manual_override_rate: Optional[float] = None
    attribution_ratio: Optional[float] = None
    date: Optional[str] = None

