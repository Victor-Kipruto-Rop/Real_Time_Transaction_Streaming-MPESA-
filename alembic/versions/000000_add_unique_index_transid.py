"""Add unique index on transactions.trans_id with pre-check for duplicates.

Notes:
- This revision performs a pre-check and aborts if duplicates exist.
- To create the index CONCURRENTLY, the migration must execute the CREATE INDEX CONCURRENTLY
  statement outside of a transaction. Alembic may run migrations inside a transaction by default.
  Approaches:
    * Preferred: run the CREATE UNIQUE INDEX CONCURRENTLY SQL manually on the DB (psql)
      after verifying duplicates are removed.
    * Or configure Alembic env.py to set transactional_ddl = False for Postgres.
    * Or use the pattern below which commits before issuing CONCURRENTLY (use with caution).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "000000_add_unique_index_transid"
down_revision = None
branch_labels = None
depends_on = None


def _has_duplicates(conn):
    result = conn.execute(
        sa.text(
            "SELECT trans_id FROM transactions GROUP BY trans_id HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).fetchone()
    return result is not None


def upgrade():
    conn = op.get_bind()

    # 1) Pre-check duplicates and abort if any exist
    if _has_duplicates(conn):
        raise RuntimeError(
            "Cannot create unique index: duplicate trans_id values exist. "
            "Run the provided dedupe script or SQL to remove duplicates, then retry."
        )

    # 2) Create index.
    # Recommended: create the index CONCURRENTLY to avoid locking writes on large tables.
    # CONCURRENTLY cannot run inside a transaction; Alembic runs inside a transaction by default.
    # Two safe options:
    #  - Run the CREATE UNIQUE INDEX CONCURRENTLY command manually (psql).
    #  - Or ensure your Alembic env.py sets transactional_ddl = False.
    #
    # Below: try to execute CONCURRENTLY by committing the current transaction around it.
    # NOTE: This pattern issues COMMIT/BEGIN and may not be accepted in all Alembic setups.
    conn.execute(sa.text("COMMIT"))
    conn.execute(
        sa.text(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_transactions_trans_id ON transactions (trans_id)"
        )
    )
    conn.execute(sa.text("BEGIN"))


def downgrade():
    conn = op.get_bind()
    # Drop index concurrently (non-transactional)
    conn.execute(sa.text("COMMIT"))
    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS ux_transactions_trans_id"))
    conn.execute(sa.text("BEGIN"))
