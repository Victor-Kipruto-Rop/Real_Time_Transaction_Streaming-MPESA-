"""
FastAPI Configuration Module
Complete settings management for production deployment
"""

from typing import List
import os

from pydantic import ConfigDict, ValidationError, ValidationInfo, field_validator
from pydantic_settings import BaseSettings


_INSECURE_SECRET_PATTERNS = (
    "admin123",
    "change_me",
    "change-me",
    "default-secret",
    "dev-secret",
    "example",
    "letmein",
    "placeholder",
    "replace_me",
    "your_secure_token_here",
)


def _normalize_secret_env() -> None:
    env_file = ".env"
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = [segment.strip() for segment in line.split("=", 1)]
                if key in {
                    "POSTGRES_PASSWORD",
                    "GRAFANA_ADMIN_PASSWORD",
                    "SECRET_KEY",
                    "UI_TOKEN",
                    "WEBHOOK_SIGNING_SECRET",
                    "DARAJA_CONSUMER_SECRET",
                    "DARAJA_PASSKEY",
                    "REDIS_PASSWORD",
                    "SMTP_PASSWORD",
                }:
                    candidate = value.strip()
                    lowered = candidate.lower()
                    if candidate and (lowered == "set_me_via_env" or any(pattern in lowered for pattern in _INSECURE_SECRET_PATTERNS)):
                        os.environ[key] = ""

    for key in {
        "POSTGRES_PASSWORD",
        "GRAFANA_ADMIN_PASSWORD",
        "SECRET_KEY",
        "UI_TOKEN",
        "WEBHOOK_SIGNING_SECRET",
        "DARAJA_CONSUMER_SECRET",
        "DARAJA_PASSKEY",
        "REDIS_PASSWORD",
        "SMTP_PASSWORD",
    }:
        value = os.getenv(key)
        if value is None:
            continue
        candidate = str(value).strip()
        if candidate == "":
            continue
        lowered = candidate.lower()
        if lowered == "set_me_via_env" or any(pattern in lowered for pattern in _INSECURE_SECRET_PATTERNS):
            os.environ[key] = ""


class Settings(BaseSettings):
    """Application settings from environment"""

    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

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

    @staticmethod
    def _reject_placeholder_secret(value: str, field_name: str) -> str:
        candidate = str(value or "").strip()
        if candidate == "":
            return value
        lowered = candidate.lower()
        if lowered == "set_me_via_env" or any(pattern in lowered for pattern in _INSECURE_SECRET_PATTERNS):
            raise ValueError(f"{field_name} must not use a placeholder or non-default secret value")
        return value

    @field_validator(
        "POSTGRES_PASSWORD",
        "SECRET_KEY",
        "GRAFANA_ADMIN_PASSWORD",
        "UI_TOKEN",
        "WEBHOOK_SIGNING_SECRET",
        "DARAJA_CONSUMER_SECRET",
        "DARAJA_PASSKEY",
        "REDIS_PASSWORD",
        "SMTP_PASSWORD",
        mode="before",
    )
    @classmethod
    def _validate_secret(cls, value: str, info: ValidationInfo) -> str:
        if value is None:
            return value
        return cls._reject_placeholder_secret(value, info.field_name)

    # Database
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5433))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "mpesa_analytics")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "data_engineer")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
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
    KAFKA_TOPIC_TRANSACTIONS: str = os.getenv(
        "KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions"
    )
    KAFKA_GROUP_ID: str = os.getenv("KAFKA_GROUP_ID", "mpesa_streaming_group")

    # Grafana
    GRAFANA_URL: str = os.getenv("GRAFANA_URL", "http://localhost:3000")
    GRAFANA_ADMIN_PASSWORD: str = os.getenv("GRAFANA_ADMIN_PASSWORD", "")

    # Security & UI
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    UI_TOKEN: str = os.getenv("UI_TOKEN", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_HOURS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", 24))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))
    WEBHOOK_SIGNING_SECRET: str = os.getenv("WEBHOOK_SIGNING_SECRET", "")
    REQUIRE_WEBHOOK_SIGNATURE: bool = (
        os.getenv("REQUIRE_WEBHOOK_SIGNATURE", "true").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    REPLAY_TTL_SECONDS: int = int(os.getenv("REPLAY_TTL_SECONDS", 300))
    KAFKA_DLQ_TOPIC: str = os.getenv("KAFKA_DLQ_TOPIC", "mpesa-transactions-dlq")
    KAFKA_RETRY_TOPIC: str = os.getenv("KAFKA_RETRY_TOPIC", "mpesa-transactions-retry")
    KAFKA_RETRY_MAX_ATTEMPTS: int = int(os.getenv("KAFKA_RETRY_MAX_ATTEMPTS", 3))
    KAFKA_RETRY_BACKOFF_SECONDS: int = int(
        os.getenv("KAFKA_RETRY_BACKOFF_SECONDS", 2)
    )

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


_normalize_secret_env()
try:
    settings = Settings()
except ValidationError:
    _normalize_secret_env()
    settings = Settings()
