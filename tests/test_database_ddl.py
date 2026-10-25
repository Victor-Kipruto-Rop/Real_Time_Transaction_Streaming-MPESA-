"""Database bootstrap DDL must be valid for the supported SQL dialects."""

from app.database.connection import _raw_transactions_table_ddl


def test_postgres_bootstrap_uses_postgres_identity_syntax():
    ddl = _raw_transactions_table_ddl("postgresql").upper()

    assert "BIGSERIAL PRIMARY KEY" in ddl
    assert "AUTOINCREMENT" not in ddl
    assert "SOURCE VARCHAR(64)" in ddl
    assert "PAYLOAD JSONB" in ddl
    assert "TRANSACTION_TIME VARCHAR(32)" in ddl


def test_sqlite_bootstrap_uses_sqlite_identity_syntax():
    ddl = _raw_transactions_table_ddl("sqlite").upper()

    assert "INTEGER PRIMARY KEY AUTOINCREMENT" in ddl
    assert "BIGSERIAL" not in ddl
    assert "SOURCE VARCHAR(64)" in ddl
    assert "PAYLOAD TEXT" in ddl
    assert "TRANSACTION_TIME VARCHAR(32)" in ddl


def test_unsupported_dialect_fails_explicitly():
    import pytest

    with pytest.raises(ValueError, match="Unsupported database dialect"):
        _raw_transactions_table_ddl("mysql")
