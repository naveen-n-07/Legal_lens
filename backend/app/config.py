"""
config.py - Environment & Application Configuration Settings
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore

class Settings(BaseSettings):
    PROJECT_NAME: str = "METRIX-LM AI Compliance Inspector"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "metrix-lm-super-secret-jwt-key-2026-sih"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database Settings
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DEFAULT_DB_PATH: str = os.path.join(BASE_DIR, "metrix_lm.db").replace("\\", "/")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

    # MinIO / S3 Storage Settings
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "metrix-inspections")

    # Confidence Thresholds for OCR Quality & Verification
    CONFIDENCE_THRESHOLD: float = 85.0
    OCR_REVIEW_THRESHOLD: float = 75.0
    OCR_HIGH_CONFIDENCE_THRESHOLD: float = 90.0

    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()
