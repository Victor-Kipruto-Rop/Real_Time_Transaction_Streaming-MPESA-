"""SQLAlchemy connection configuration and bootstrap helpers."""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()


def _database_url() -> str:
    """Build the runtime database URL, defaulting to SQLite for local tests."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    if os.getenv("USE_SQLITE_FOR_TESTS", "0").lower() in {"1", "true", "yes", "on"}:
        sqlite_path = ".tmp/mpesa_test.db"
        os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
        return f"sqlite:///{sqlite_path}"

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5433")
    db_name = os.getenv("POSTGRES_DB", "mpesa_analytics")
    user = os.getenv("POSTGRES_USER", "data_engineer")
    password = os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"


engine = create_engine(
    _database_url(),
    pool_pre_ping=True,
    future=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def init_db() -> None:
    """Create all tables required by the app and idempotency layer."""
    from app.database.models import Base as ModelsBase

    ModelsBase.metadata.create_all(bind=engine)


def check_db() -> bool:
    """Validate the database connectivity."""
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
