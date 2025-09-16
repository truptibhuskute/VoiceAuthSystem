"""
Core configuration settings for the Voice Authentication System
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Voice Authentication System"
    PROJECT_VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-minimum-32-characters-long")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # Database - Using SQLite for demo (easy setup)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./voiceauth.db"  # SQLite for easy demo
    )
    
    # Voice Processing Settings
    SAMPLE_RATE: int = 16000  # Standard for voice processing
    AUDIO_DURATION: float = 3.0  # Seconds for enrollment/verification
    MIN_AUDIO_DURATION: float = 1.0
    MAX_AUDIO_DURATION: float = 10.0
    
    # ML Model Settings
    MODEL_PATH: str = os.getenv("MODEL_PATH", "./ml_models/")
    FEATURE_DIM: int = 40  # MFCC features
    EMBEDDING_DIM: int = 256
    
    # Security Thresholds
    VERIFICATION_THRESHOLD: float = 0.85  # Similarity threshold for verification
    LIVENESS_THRESHOLD: float = 0.7  # Anti-spoofing threshold
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_AUDIO_FORMATS: list[str] = ["wav", "mp3", "m4a", "ogg"]
    
    # Redis (for caching) - Optional
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://localhost:3000",
        "https://localhost:8080",
    ]
    
    # Development
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
