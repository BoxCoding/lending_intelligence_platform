"""Application configuration loaded from environment variables."""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "LendIQ - Retail Lending Intelligence Platform"
    version: str = "1.0.0"
    environment: str = os.getenv("ENVIRONMENT", "development")

    # LLM
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    embedding_model: str = "text-embedding-004"

    # Firestore
    google_application_credentials: str = ""
    firebase_credentials_json: str = ""  # inline JSON (for Render/Vercel env vars)
    firestore_project_id: str = ""
    firestore_database: str = "(default)"  # named DBs supported, e.g. "LendIQ"
    # Local JSON persistence fallback when Firestore is not configured
    local_store_path: str = "data/store"

    # ML artifacts
    model_dir: str = os.getenv("MODEL_DIR", "../ml/models")

    # API
    cors_origins: str = "http://localhost:3000,https://*.vercel.app"

    # Lending policy knobs
    max_foir: float = 0.55  # max Fixed Obligation to Income Ratio
    min_lead_score_hot: int = 68
    min_lead_score_warm: int = 48

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
