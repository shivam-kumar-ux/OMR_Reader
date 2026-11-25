import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_SECRET_KEY: str = "omr-secret-key-production-change-secure"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "sqlite:///./omr_local.db"
    DATABASE_UR: Optional[str] = None
    APP_SECRET_KE: Optional[str] = None
    IS_SERVERLESS: bool = False

    def model_post_init(self, __context):
        if self.DATABASE_UR and self.DATABASE_URL == "sqlite:///./omr_local.db":
            self.DATABASE_URL = self.DATABASE_UR
        if self.APP_SECRET_KE and self.APP_SECRET_KEY == "omr-secret-key-production-change-secure":
            self.APP_SECRET_KEY = self.APP_SECRET_KE

    # Storage: "local", "azure_blob", "vercel_blob"
    STORAGE_PROVIDER: str = "local"
    STORAGE_LOCAL_DIR: str = "./storage"
    STORAGE_WATCH_DIR: str = "./scans_input"

    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_CONTAINER_NAME: str = "omr-sheets"
    BLOB_READ_WRITE_TOKEN: Optional[str] = None

    # OMR & Accuracy Thresholds
    CONFIDENCE_THRESHOLD_AUTO_ACCEPT: float = 0.88
    BUBBLE_FILL_THRESHOLD: float = 0.45
    BUBBLE_UNCERTAIN_LOW: float = 0.30
    BUBBLE_UNCERTAIN_HIGH: float = 0.45
    OCR_NAME_SIMILARITY_THRESHOLD: float = 0.75

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
