"""Database models using SQLAlchemy."""
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from config.settings import settings

Base = declarative_base()


class User(Base):
    """User/Editor model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    overrides = relationship("Override", back_populates="user")
    style_memories = relationship("StyleMemory", back_populates="approver")


class Book(Base):
    """Book model."""
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title_en = Column(String(500), nullable=False)
    title_az = Column(String(500))
    author = Column(String(255))
    year = Column(Integer)
    file_path = Column(String(1000))
    file_type = Column(String(50))
    status = Column(String(50), default="uploaded")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    segments = relationship("Segment", back_populates="book", cascade="all, delete-orphan")


class Segment(Base):
    """Translation segment model."""
    __tablename__ = "segments"
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_index = Column(Integer, nullable=False)
    source_en = Column(Text, nullable=False)
    translated_az = Column(Text)
    status = Column(String(50), default="pending")
    
    # Metrics columns
    style_similarity_score = Column(Float, nullable=True)
    from_style_memory = Column(Boolean, default=False, index=True)
    has_override = Column(Boolean, default=False)
    override_similarity_score = Column(Float, nullable=True)
    override_percentage = Column(Float, nullable=True)  # Percentage of translation changed by override (0-100)
    translation_source = Column(String(50), default="model")  # 'model' or 'style_memory'
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    book = relationship("Book", back_populates="segments")
    overrides = relationship("Override", back_populates="segment", cascade="all, delete-orphan")
    style_memory = relationship("StyleMemory", back_populates="segment", uselist=False)


class StyleMemory(Base):
    """Style memory for approved translations."""
    __tablename__ = "style_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(Integer, ForeignKey("segments.id", ondelete="SET NULL"), nullable=True)
    source_en = Column(Text, nullable=False, index=True)
    preferred_az = Column(Text, nullable=False)
    embedding = Column(Vector(768))
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, server_default=func.now())
    engine = Column(String(50))
    similarity_score = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    segment = relationship("Segment", back_populates="style_memory")
    approver = relationship("User", back_populates="style_memories")


class Override(Base):
    """Override history model."""
    __tablename__ = "overrides"
    
    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(Integer, ForeignKey("segments.id", ondelete="CASCADE"), nullable=False, index=True)
    old_translation = Column(Text)
    new_translation = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    engine = Column(String(50), nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    
    # Relationships
    segment = relationship("Segment", back_populates="overrides")
    user = relationship("User", back_populates="overrides")


class TrainingRun(Base):
    """Training run tracking model."""
    __tablename__ = "training_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), nullable=False)
    model_path = Column(String(1000))
    train_samples = Column(Integer)
    validation_samples = Column(Integer)
    bleu_score = Column(Float)
    chrf_score = Column(Float)
    style_similarity_score = Column(Float)
    status = Column(String(50), default="training")
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    notes = Column(Text)


class Metric(Base):
    """Daily metrics tracking model."""
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    bleu_score = Column(Float)
    chrf_score = Column(Float)
    style_similarity_score = Column(Float)
    manual_override_rate = Column(Float)
    attribution_ratio = Column(Float)
    total_segments = Column(Integer, default=0)
    overridden_segments = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


# Database engine and session
engine = create_engine(settings.database_url, echo=settings.debug)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

