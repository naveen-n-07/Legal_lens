"""
config.py - Environment & Application Configuration Settings
"""

import os
from pydantic_settings import BaseSettings  # type: ignore

class Settings(BaseSettings):
    PROJECT_NAME: str = "METRIX-LM AI Compliance Inspector"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "metrix-lm-super-secret-jwt-key-2026-sih"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./metrix_lm.db")

    # MinIO / S3 Storage Settings
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "metrix-inspections")

    # Confidence Threshold for Route 7B Trigger
    CONFIDENCE_THRESHOLD: float = 85.0

    class Config:
        case_sensitive = True

settings = Settings()
