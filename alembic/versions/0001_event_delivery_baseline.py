"""Versioned bootstrap for current ORM tables and raw transaction storage.

Existing installations are upgraded non-destructively: create missing ORM tables and
add raw/callback/DLQ tables if absent. Existing rows are not deleted or rewritten.
"""
from alembic import op
from sqlalchemy import text

revision = "0001_event_delivery_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    from app.database.connection import Base
    from app.database import models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    dialect = bind.dialect.name

    if dialect == "postgresql":
        bind.execute(text("""
            CREATE TABLE IF NOT EXISTS mpesa_transactions_raw (
                id BIGSERIAL PRIMARY KEY,
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
                payload JSONB,
                processed_at TIMESTAMP,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        bind.execute(text("ALTER TABLE mpesa_transactions_raw ADD COLUMN IF NOT EXISTS source VARCHAR(64)"))
        bind.execute(text("ALTER TABLE mpesa_transactions_raw ADD COLUMN IF NOT EXISTS payload JSONB"))
    elif dialect == "sqlite":
        bind.execute(text("""
            CREATE TABLE IF NOT EXISTS mpesa_transactions_raw (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                payload TEXT,
                processed_at TIMESTAMP,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        columns = {row[1] for row in bind.execute(text("PRAGMA table_info(mpesa_transactions_raw)"))}
        if "source" not in columns:
            bind.execute(text("ALTER TABLE mpesa_transactions_raw ADD COLUMN source VARCHAR(64)"))
        if "payload" not in columns:
            bind.execute(text("ALTER TABLE mpesa_transactions_raw ADD COLUMN payload TEXT"))
    else:
        raise RuntimeError(f"Unsupported migration dialect: {dialect}")

    # Fail the migration if historical duplicate transaction IDs prevent the
    # database constraint from being established; never delete financial records.
    bind.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_mpesa_transactions_raw_transaction_id
        ON mpesa_transactions_raw (transaction_id)
    """))


def downgrade():
    # This is a non-destructive baseline/bridge migration for repositories that may
    # already contain operational data. Use a reviewed forward migration to change it.
    raise RuntimeError("Destructive downgrade is intentionally disabled; restore from backup instead.")
