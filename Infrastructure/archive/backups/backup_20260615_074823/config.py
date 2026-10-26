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
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5432))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "mpesa_analytics")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "data_engineer")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "change_me_to_secure_password")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", 20))

    @property
    def DATABASE_URL(self) -> str:
        # Backward compatibility for DB_ variables
        host = os.getenv("DB_HOST", self.POSTGRES_HOST)
        port = os.getenv("DB_PORT", self.POSTGRES_PORT)
        db = os.getenv("DB_NAME", self.POSTGRES_DB)
        user = os.getenv("DB_USER", self.POSTGRES_USER)
        pwd = os.getenv("DB_PASSWORD", self.POSTGRES_PASSWORD)
        return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"

    # Kafka
    KAFKA_BROKERS: str = os.getenv("KAFKA_BROKERS", "localhost:9092")
    KAFKA_TOPIC_TRANSACTIONS: str = os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions")
    KAFKA_GROUP_ID: str = os.getenv("KAFKA_GROUP_ID", "mpesa_streaming_group")

    # Grafana
    GRAFANA_URL: str = os.getenv("GRAFANA_URL", "http://localhost:3000")
    GRAFANA_ADMIN_PASSWORD: str = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin123")

    # Security & UI
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    UI_TOKEN: str = os.getenv("UI_TOKEN", "your_secure_token_here")
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
