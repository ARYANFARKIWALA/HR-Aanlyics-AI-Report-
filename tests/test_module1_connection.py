"""Unit tests for Module 1: Database Connection & Schema Management."""

import pytest
from backend.database.connection_manager import (
    connection_manager, DatabaseConnectionConfig
)
from backend.database.dialect import DatabaseType, get_dialect_rules
from backend.database.schema_manager import SchemaManager


def test_dialect_rules_mapping():
    """Verify per-dialect date functions and LIMIT/TOP handling."""
    sqlite_rules = get_dialect_rules("sqlite")
    assert sqlite_rules.limit_syntax == "LIMIT"
    assert "JULIANDAY" in sqlite_rules.format_tenure_calc("hire_date", "termination_date")

    tsql_rules = get_dialect_rules("sqlserver")
    assert tsql_rules.limit_syntax == "TOP"
    assert tsql_rules.format_limit("SELECT * FROM employees", 10) == "SELECT TOP 10 * FROM employees"

    pg_rules = get_dialect_rules("postgresql")
    assert pg_rules.limit_syntax == "LIMIT"
    assert "EXTRACT" in pg_rules.format_tenure_calc("hire_date", "termination_date")


def test_credential_encryption():
    """Verify credentials/knowledge split and Fernet encryption."""
    raw_url = "postgresql://hr_admin:superSecretPass123@db.prod.internal:5432/hr_dw"
    cfg = DatabaseConnectionConfig(
        database_id="prod_dw",
        display_name="Production DW",
        db_type="postgresql",
        connection_url=raw_url
    )

    encrypted = cfg.encrypt_url()
    assert encrypted != raw_url
    assert "superSecretPass123" not in encrypted

    decrypted = DatabaseConnectionConfig.decrypt_url(encrypted)
    assert decrypted == raw_url


def test_connection_testing():
    """Verify Component 1: reachability test without persisting."""
    # Test valid SQLite in-memory
    success, msg, diag = connection_manager.test_connection("sqlite", "sqlite:///:memory:")
    assert success is True
    assert "Connection test succeeded" in msg

    # Test invalid connection
    fail_success, fail_msg, _ = connection_manager.test_connection("postgresql", "postgresql://invalid_host:9999/none")
    assert fail_success is False


def test_schema_discovery_and_allowlist():
    """Verify automatic schema discovery and allowlist source of truth."""
    schema = connection_manager.get_schema("sqlite_hr_default")
    assert schema is not None
    assert len(schema.tables) > 0
    assert len(schema.schema_hash) == 64  # SHA-256

    # Verify allowlist check
    assert schema.is_table_allowed("employees") is True
    assert schema.is_table_allowed("departments") is True
    assert schema.is_table_allowed("malicious_hacker_table") is False
