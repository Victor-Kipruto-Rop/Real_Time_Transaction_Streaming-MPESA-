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


def _raw_transactions_table_ddl(dialect_name: str) -> str:
    """Return table DDL valid for the supported SQLite and PostgreSQL dialects."""
    if dialect_name not in {"sqlite", "postgresql"}:
        raise ValueError(
            f"Unsupported database dialect for raw transaction bootstrap: {dialect_name}"
        )
    payload_type = "TEXT" if dialect_name == "sqlite" else "JSONB"
    id_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if dialect_name == "sqlite" else "BIGSERIAL PRIMARY KEY"
    return f"""
        CREATE TABLE IF NOT EXISTS mpesa_transactions_raw (
            id {id_type},
            transaction_id VARCHAR(128) NOT NULL,
            phone_number VARCHAR(32),
            amount NUMERIC(18,2),
            business_shortcode VARCHAR(64),
            transaction_time VARCHAR(32),
            transaction_status VARCHAR(32),
            payment_method VARCHAR(32),
            reference VARCHAR(128),
            account_reference VARCHAR(128),
            merchant_id VARCHAR(128),
            region VARCHAR(64),
            source VARCHAR(64),
            payload {payload_type},
            processed_at TIMESTAMP,
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """


def ensure_transaction_id_unique_index() -> None:
    """Ensure the raw transaction table schema and transaction ID uniqueness."""
    dialect_name = engine.dialect.name
    with engine.begin() as conn:
        conn.execute(text(_raw_transactions_table_ddl(dialect_name)))

        # Existing databases created by older versions may have the table but not
        # the fields consumed by streaming.kafka_consumer. Migrate additively.
        if dialect_name == "postgresql":
            conn.execute(text(
                "ALTER TABLE mpesa_transactions_raw "
                "ADD COLUMN IF NOT EXISTS source VARCHAR(64)"
            ))
            conn.execute(text(
                "ALTER TABLE mpesa_transactions_raw "
                "ADD COLUMN IF NOT EXISTS payload JSONB"
            ))
        else:
            existing_columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(mpesa_transactions_raw)"))
            }
            if "source" not in existing_columns:
                conn.execute(text(
                    "ALTER TABLE mpesa_transactions_raw ADD COLUMN source VARCHAR(64)"
                ))
            if "payload" not in existing_columns:
                conn.execute(text(
                    "ALTER TABLE mpesa_transactions_raw ADD COLUMN payload TEXT"
                ))

            # SQLite does not automatically clean historical duplicates before a
            # unique index is created. Remove duplicates first.
            conn.execute(text("""
                WITH ranked AS (
                    SELECT id,
                           ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY id) AS rn
                    FROM mpesa_transactions_raw
                    WHERE transaction_id IS NOT NULL
                )
                DELETE FROM mpesa_transactions_raw
                WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
            """))

        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_mpesa_transactions_raw_transaction_id
            ON mpesa_transactions_raw (transaction_id)
        """))

def init_db() -> None:
    """Create all tables required by the app and idempotency layer."""
    from app.database.models import Base as ModelsBase

    try:
        ModelsBase.metadata.create_all(bind=engine)
        ensure_transaction_id_unique_index()
    except Exception:
        # Fail fast for bootstrap errors so the service does not start with a broken
        # schema or a partial set of tables.
        raise


def check_db() -> bool:
    """Validate the database connectivity."""
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
