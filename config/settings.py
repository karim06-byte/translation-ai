"""Application configuration settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = {
        'protected_namespaces': ('settings_',),
        'env_file': '.env',
        'case_sensitive': False
    }
    
    # Database
    database_url: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    
    # Model
    model_name: str = "facebook/nllb-200-distilled-1.3B"
    model_cache_dir: str = "./models"
    output_dir: str = "./outputs"
    
    # API Keys
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Retraining
    retrain_threshold: int = 500
    retrain_interval_days: int = 14
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True


settings = Settings()

