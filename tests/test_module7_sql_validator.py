"""Unit and Integration Tests for Module 7 — SQL Validator & Security Engine."""

import pytest
import datetime
import hashlib
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import SessionLocal, init_db
from backend.database.models import User
from backend.database.models_auth import ColumnPermission
from backend.database.models_validation import SQLValidationAuditLog
from sql_validator.schemas import SQLValidationRequest
from sql_validator.service import SQLValidatorService


@pytest.fixture(scope="function")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_valid_select_query_approval(db_session):
    """Test 1: Valid clean SELECT query is APPROVED with validation_id and low risk."""
    service = SQLValidatorService(db=db_session)
    req = SQLValidationRequest(
        sql="SELECT e.first_name, e.last_name, d.name AS department FROM employees e JOIN departments d ON e.department_id = d.id WHERE e.status = 'Active' AND e.is_current = 1 LIMIT 25;",
        database_id="sqlite_hr_default",
        user_role="hr_analyst"
    )
    resp = service.validate_query(req)

    assert resp.status == "APPROVED"
    assert resp.can_execute is True
    assert resp.validation_id is not None
    assert resp.validation_id.startswith("val_")
    assert resp.risk_score < 40.0
    assert resp.risk_level in ["LOW", "MEDIUM"]
    assert len(resp.violations) == 0
    assert resp.sql_hash == hashlib.sha256(resp.sanitized_sql.encode("utf-8")).hexdigest()

    # Check database persistence
    audit = db_session.query(SQLValidationAuditLog).filter(
        SQLValidationAuditLog.validation_id == resp.validation_id
    ).first()
    assert audit is not None
    assert audit.status == "APPROVED"


def test_prohibited_mutations_rejection(db_session):
    """Test 2: Destructive DDL/DML queries are REJECTED with CRITICAL risk."""
    service = SQLValidatorService(db=db_session)
    bad_queries = [
        "DROP TABLE employees;",
        "DELETE FROM compensation_history WHERE id > 0;",
        "UPDATE employees SET status = 'Terminated';",
        "INSERT INTO departments (name, code) VALUES ('Hacked', 'HCK');",
        "ALTER TABLE employees ADD COLUMN malicious TEXT;"
    ]

    for sql in bad_queries:
        req = SQLValidationRequest(sql=sql, database_id="sqlite_hr_default")
        resp = service.validate_query(req)
        assert resp.status == "REJECTED"
        assert resp.can_execute is False
        assert resp.validation_id is None
        assert resp.risk_score == 100.0
        assert resp.risk_level == "CRITICAL"
        assert len(resp.violations) > 0


def test_multi_statement_chaining_rejection(db_session):
    """Test 3: Multiple statement injection chaining is REJECTED."""
    service = SQLValidatorService(db=db_session)
    req = SQLValidationRequest(
        sql="SELECT first_name FROM employees; DROP TABLE departments;",
        database_id="sqlite_hr_default"
    )
    resp = service.validate_query(req)

    assert resp.status == "REJECTED"
    assert resp.can_execute is False
    assert any("multiple statements" in v.lower() for v in resp.violations)


def test_schema_hallucination_detection(db_session):
    """Test 4: Queries referencing non-existent tables or columns are REJECTED."""
    service = SQLValidatorService(db=db_session)

    # Hallucinated table
    req_tbl = SQLValidationRequest(
        sql="SELECT * FROM fictional_tax_records_2026;",
        database_id="sqlite_hr_default"
    )
    resp_tbl = service.validate_query(req_tbl)
    assert resp_tbl.status == "REJECTED"
    assert any("fictional_tax_records_2026" in v for v in resp_tbl.violations)

    # Hallucinated column
    req_col = SQLValidationRequest(
        sql="SELECT employees.non_existent_secret_key FROM employees;",
        database_id="sqlite_hr_default"
    )
    resp_col = service.validate_query(req_col)
    assert resp_col.status == "REJECTED"
    assert any("non_existent_secret_key" in v for v in resp_col.violations)


def test_cartesian_join_detection(db_session):
    """Test 5: Cartesian products (CROSS JOIN / unconditional join) are REJECTED."""
    service = SQLValidatorService(db=db_session)

    # Comma join without where
    req1 = SQLValidationRequest(
        sql="SELECT e.first_name, d.name FROM employees e, departments d;",
        database_id="sqlite_hr_default"
    )
    resp1 = service.validate_query(req1)
    assert resp1.status == "REJECTED"
    assert any("cartesian" in v.lower() for v in resp1.violations)

    # Explicit cross join
    req2 = SQLValidationRequest(
        sql="SELECT e.first_name, d.name FROM employees e CROSS JOIN departments d;",
        database_id="sqlite_hr_default"
    )
    resp2 = service.validate_query(req2)
    assert resp2.status == "REJECTED"
    assert any("cartesian" in v.lower() for v in resp2.violations)


def test_dangerous_functions_rejection(db_session):
    """Test 6: Injected dangerous or OS-level functions are REJECTED."""
    service = SQLValidatorService(db=db_session)
    dangerous_sqls = [
        "SELECT xp_cmdshell('whoami') FROM employees;",
        "SELECT benchmark(10000000, MD5(1)) FROM employees;",
        "SELECT pg_sleep(10) FROM employees;",
    ]

    for sql in dangerous_sqls:
        req = SQLValidationRequest(sql=sql, database_id="sqlite_hr_default")
        resp = service.validate_query(req)
        assert resp.status == "REJECTED"
        assert resp.can_execute is False
        assert any("forbidden" in v.lower() or "prohibited" in v.lower() for v in resp.violations)


def test_column_level_security_enforcement(db_session):
    """Test 7: Column-Level Security rejects access to restricted columns for non-admin."""
    # Create test user
    uid_str = str(int(datetime.datetime.now().timestamp() * 1000))[-6:]
    uname = f"cls_analyst_{uid_str}"
    user = User(
        username=uname,
        full_name="CLS Analyst",
        email=f"{uname}@test.com",
        hashed_password="x",
        role="hr_analyst",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Define restriction rule on 'tax_id' for this user
    cp = ColumnPermission(
        user_id=user.id,
        database_id="sqlite_hr_default",
        table_name="employees",
        column_name="ethnicity",
        is_allowed=False  # Denied!
    )
    db_session.add(cp)
    db_session.commit()

    service = SQLValidatorService(db=db_session)
    req = SQLValidationRequest(
        sql="SELECT id, first_name, ethnicity FROM employees WHERE is_current = 1;",
        database_id="sqlite_hr_default",
        user_id=user.id
    )
    resp = service.validate_query(req)
    assert resp.status == "REJECTED"
    assert any("column-level security" in v.lower() for v in resp.violations)


def test_select_star_policy_warning(db_session):
    """Test 8: Unconstrained SELECT * generates warning and elevated risk."""
    service = SQLValidatorService(db=db_session)
    req = SQLValidationRequest(
        sql="SELECT * FROM departments;",
        database_id="sqlite_hr_default",
        allow_select_star=False
    )
    resp = service.validate_query(req)
    # Passed with warning
    assert resp.status == "APPROVED"
    assert any("SELECT *" in w for w in resp.warnings)


def test_fastapi_sql_validator_endpoints(client):
    """Test 9: FastAPI endpoints for validation, tokens, policies, and audit."""
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Validate SQL endpoint
    val_resp = client.post(
        "/api/sql-validator/validate",
        headers=headers,
        json={
            "sql": "SELECT name, code FROM departments WHERE budget > 1000000;",
            "database_id": "sqlite_hr_default"
        }
    )
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["status"] == "APPROVED"
    assert val_data["validation_id"] is not None

    val_id = val_data["validation_id"]

    # 2. Check token endpoint
    token_resp = client.get(f"/api/sql-validator/tokens/{val_id}", headers=headers)
    assert token_resp.status_code == 200
    token_data = token_resp.json()
    assert token_data["status"] == "APPROVED"
    assert token_data["is_expired"] is False

    # 3. Policies endpoint
    policy_resp = client.get("/api/sql-validator/policies", headers=headers)
    assert policy_resp.status_code == 200
    assert "safe_functions" in policy_resp.json()

    # 4. Audit endpoint
    audit_resp = client.get("/api/sql-validator/audit", headers=headers)
    assert audit_resp.status_code == 200
    assert len(audit_resp.json()["validation_logs"]) >= 1
