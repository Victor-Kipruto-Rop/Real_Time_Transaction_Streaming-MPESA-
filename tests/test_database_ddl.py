"""Database bootstrap DDL must be valid for the supported SQL dialects."""

from app.database.connection import _raw_transactions_table_ddl


def test_postgres_bootstrap_uses_postgres_identity_syntax():
    ddl = _raw_transactions_table_ddl("postgresql").upper()

    assert "BIGSERIAL PRIMARY KEY" in ddl
    assert "AUTOINCREMENT" not in ddl
    assert "SOURCE VARCHAR(64)" in ddl
    assert "PAYLOAD JSONB" in ddl
    assert "TRANSACTION_TIME VARCHAR(32)" in ddl
    assert "RECEIVED_AT TIMESTAMP" in ddl


def test_sqlite_bootstrap_uses_sqlite_identity_syntax():
    ddl = _raw_transactions_table_ddl("sqlite").upper()

    assert "INTEGER PRIMARY KEY AUTOINCREMENT" in ddl
    assert "BIGSERIAL" not in ddl
    assert "SOURCE VARCHAR(64)" in ddl
    assert "PAYLOAD TEXT" in ddl
    assert "TRANSACTION_TIME VARCHAR(32)" in ddl
    assert "RECEIVED_AT TIMESTAMP" in ddl


def test_unsupported_dialect_fails_explicitly():
    import pytest

    with pytest.raises(ValueError, match="Unsupported database dialect"):
        _raw_transactions_table_ddl("mysql")



def test_sqlite_duplicate_transaction_ids_are_preserved_and_raise(monkeypatch):
    from sqlalchemy import create_engine, text
    import pytest
    import app.database.connection as connection

    test_engine = create_engine("sqlite://")
    monkeypatch.setattr(connection, "engine", test_engine)
    with test_engine.begin() as conn:
        conn.execute(text(connection._raw_transactions_table_ddl("sqlite")))
        conn.execute(
            text(
                "INSERT INTO mpesa_transactions_raw (transaction_id, amount) "
                "VALUES ('DUPLICATE-RECEIPT', 10), ('DUPLICATE-RECEIPT', 20)"
            )
        )

    with pytest.raises(RuntimeError, match="Duplicate transaction_id"):
        connection.ensure_transaction_id_unique_index()

    with test_engine.connect() as conn:
        count = conn.execute(
            text(
                "SELECT COUNT(*) FROM mpesa_transactions_raw "
                "WHERE transaction_id = 'DUPLICATE-RECEIPT'"
            )
        ).scalar_one()
    assert count == 2
    test_engine.dispose()
