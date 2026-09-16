"""Comprehensive Unit and Integration Tests for Phase 7 — SQL Validation and Security Engine."""

import pytest

from backend.database.connection import SessionLocal, init_db
from sql_validator.schemas import SQLValidationRequest
from sql_validator.service import SQLValidatorService


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_validate_canonical_attrition_query(db_session):
    """Test validation of canonical monthly attrition query."""
    service = SQLValidatorService(db=db_session)
    sql = (
        "SELECT departments.name, strftime('%Y-%m', employees.termination_date) AS month, "
        "COUNT(employees.id) AS attrition_count "
        "FROM employees "
        "INNER JOIN departments ON employees.department_id = departments.id "
        "WHERE employees.status = 'Terminated' "
        "AND employees.termination_date >= '2026-01-01' "
        "AND employees.termination_date <= '2026-12-31' "
        "GROUP BY departments.name, strftime('%Y-%m', employees.termination_date) "
        "ORDER BY month ASC, departments.name ASC;"
    )
    res = service.validate_query(SQLValidationRequest(
        sql=sql,
        database_id="sqlite_hr_default",
        user_role="admin"
    ))

    assert res.status == "APPROVED"
    assert res.is_valid is True
    assert res.can_execute is True
    assert res.validation_id is not None
    assert res.validation_id.startswith("val_")
    assert res.safe_error_explanation is None
    assert res.timeout_seconds == 30
    assert res.max_row_limit == 5000


@pytest.mark.parametrize("mutation_sql", [
    "DROP TABLE employees;",
    "DELETE FROM employees WHERE id = 1;",
    "UPDATE employees SET status = 'Terminated';",
    "INSERT INTO departments (id, name, code, cost_center) VALUES (99, 'Test', 'T99', 'CC99');",
    "ALTER TABLE employees ADD COLUMN test_col VARCHAR(50);",
    "TRUNCATE TABLE employees;"
])
def test_reject_mutation_commands(db_session, mutation_sql):
    """Verify all destructive DDL and DML operations are strictly rejected."""
    service = SQLValidatorService(db=db_session)
    res = service.validate_query(SQLValidationRequest(
        sql=mutation_sql,
        database_id="sqlite_hr_default",
        user_role="admin"
    ))

    assert res.status == "REJECTED"
    assert res.is_valid is False
    assert res.can_execute is False
    assert res.validation_id is None
    assert res.safe_error_explanation is not None
    assert len(res.violations) > 0


def test_reject_multi_statement_chaining(db_session):
    """Test rejection of multi-statement SQL injection vectors."""
    service = SQLValidatorService(db=db_session)
    sql = "SELECT id FROM departments; DROP TABLE employees;"
    res = service.validate_query(SQLValidationRequest(
        sql=sql,
        database_id="sqlite_hr_default",
        user_role="admin"
    ))

    assert res.status == "REJECTED"
    assert res.is_valid is False
    assert res.can_execute is False
    assert "Multiple statements" in res.safe_error_explanation


@pytest.mark.parametrize("dangerous_func_sql", [
    "SELECT xp_cmdshell('whoami');",
    "SELECT pg_sleep(10);",
    "SELECT load_file('/etc/passwd');",
    "SELECT benchmark(1000000, MD5(1));"
])
def test_reject_dangerous_functions(db_session, dangerous_func_sql):
    """Test rejection of non-whitelisted or dangerous server functions."""
    service = SQLValidatorService(db=db_session)
    res = service.validate_query(SQLValidationRequest(
        sql=dangerous_func_sql,
        database_id="sqlite_hr_default",
        user_role="admin"
    ))

    assert res.status == "REJECTED"
    assert res.is_valid is False
    assert res.can_execute is False


@pytest.mark.parametrize("sensitive_col_sql", [
    "SELECT id, ssn FROM employees;",
    "SELECT id, password FROM users;",
    "SELECT id, bank_account_number FROM employees;",
    "SELECT id, medical_history FROM employees;"
])
def test_reject_sensitive_fields(db_session, sensitive_col_sql):
    """Test rejection of unauthorized sensitive data access (SSN, passwords, banking, medical)."""
    service = SQLValidatorService(db=db_session)
    res = service.validate_query(SQLValidationRequest(
        sql=sensitive_col_sql,
        database_id="sqlite_hr_default",
        user_role="admin"
    ))

    assert res.status == "REJECTED"
    assert res.is_valid is False
    assert res.can_execute is False
    assert "sensitive" in res.safe_error_explanation.lower() or "credential" in res.safe_error_explanation.lower()


def test_reject_cartesian_joins(db_session):
    """Test detection and rejection of Cartesian products."""
    service = SQLValidatorService(db=db_session)
    sql = "SELECT * FROM employees CROSS JOIN departments;"
    res = service.validate_query(SQLValidationRequest(
        sql=sql,
        database_id="sqlite_hr_default",
        user_role="admin"
    ))

    assert res.status == "REJECTED"
    assert res.is_valid is False
    assert res.can_execute is False
    assert "Cartesian" in res.safe_error_explanation or "join" in res.safe_error_explanation.lower()


def test_reject_unknown_tables_allowlist(db_session):
    """Test rejection of schema entities outside target database allowlist."""
    service = SQLValidatorService(db=db_session)
    sql = "SELECT * FROM fake_financial_records;"
    res = service.validate_query(SQLValidationRequest(
        sql=sql,
        database_id="sqlite_hr_default",
        user_role="admin"
    ))

    assert res.status == "REJECTED"
    assert res.is_valid is False
    assert res.can_execute is False
    assert "hallucination" in res.safe_error_explanation.lower() or "not exist" in res.safe_error_explanation.lower()
