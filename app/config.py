"""
FastAPI Configuration Module
Complete settings management for production deployment
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings from environment"""

    # Application
    APP_NAME: str = "M-Pesa Analytics Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "development"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "production"}:
            return False
        return False

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 5433))
    DB_NAME: str = os.getenv("DB_NAME", "mpesa_analytics")
    DB_USER: str = os.getenv("DB_USER", "data_engineer")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "change_me")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", 20))

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_HOURS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", 24))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))

    # HTTPS & Domain
    DOMAIN: str = os.getenv("DOMAIN", "localhost:8000")
    HTTPS_REDIRECT: bool = os.getenv("HTTPS_REDIRECT", "false").lower() == "true"
    ALLOWED_ORIGINS: List[str] = [
        "https://chamayangu.online",
        "https://api.chamayangu.online",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # Safaricom Daraja API
    DARAJA_CONSUMER_KEY: str = os.getenv("DARAJA_CONSUMER_KEY", "")
    DARAJA_CONSUMER_SECRET: str = os.getenv("DARAJA_CONSUMER_SECRET", "")
    DARAJA_BUSINESS_SHORTCODE: str = os.getenv(
        "DARAJA_BUSINESS_SHORTCODE",
        os.getenv("MPESA_BUSINESS_SHORTCODE", "8759693"),
    )
    DARAJA_PASSKEY: str = os.getenv("DARAJA_PASSKEY", os.getenv("MPESA_PASSKEY", ""))
    DARAJA_ENVIRONMENT: str = os.getenv("DARAJA_ENVIRONMENT", "sandbox")

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6380))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", 60))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # GCP
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "mpesapipeline")
    GCP_REGION: str = os.getenv("GCP_REGION", "africa-south1")

    # Email
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "kiprutovictor39@gmail.com")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
