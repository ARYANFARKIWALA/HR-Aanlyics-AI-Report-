"""Unit and Integration Tests for Module 8 — Query Execution Engine."""

import datetime
import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal, init_db
from backend.database.models import User
from backend.database.models_execution import QueryExecutionAuditLog
from backend.database.models_validation import SQLValidationAuditLog
from backend.main import app
from query_execution.schemas import ExecuteQueryRequest
from query_execution.service import QueryExecutionError, QueryExecutionService
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


def _create_approved_token(db_session, sql: str, database_id: str = "sqlite_hr_default") -> str:
    """Helper to validate and generate an APPROVED token."""
    val_service = SQLValidatorService(db=db_session)
    val_resp = val_service.validate_query(SQLValidationRequest(
        sql=sql,
        database_id=database_id,
        user_role="admin"
    ))
    assert val_resp.status == "APPROVED"
    assert val_resp.validation_id is not None
    return val_resp.validation_id


def test_valid_handshake_and_query_execution(db_session):
    """Test 1: Valid handshake executes query, preserves types, and creates audit log."""
    val_id = _create_approved_token(
        db_session,
        "SELECT id, name, code, budget FROM departments ORDER BY id ASC;"
    )

    admin_user = db_session.query(User).filter(User.username == "admin").first()
    service = QueryExecutionService(db=db_session)
    exec_req = ExecuteQueryRequest(validation_id=val_id, bypass_cache=True)
    res = service.execute(exec_req, user=admin_user)

    assert res.status == "SUCCESS"
    assert res.total_rows > 0
    assert len(res.rows) > 0
    assert "name" in res.columns
    assert "budget" in res.columns
    assert res.cached is False
    assert res.execution_id.startswith("exec_")

    # Verify type preservation
    first_row = res.rows[0]
    assert isinstance(first_row["budget"], float)
    assert isinstance(first_row["name"], str)

    # Check execution audit log
    audit = db_session.query(QueryExecutionAuditLog).filter(
        QueryExecutionAuditLog.execution_id == res.execution_id
    ).first()
    assert audit is not None
    assert audit.status == "SUCCESS"
    assert audit.row_count == res.total_rows


def test_unapproved_token_rejection(db_session):
    """Test 2: Token with status != 'APPROVED' is rejected."""
    # Create unapproved validation log manually
    fake_val_id = f"val_unapproved_{uuid.uuid4().hex[:8]}"
    audit = SQLValidationAuditLog(
        validation_id=fake_val_id,
        database_id="sqlite_hr_default",
        raw_sql="SELECT * FROM employees;",
        sanitized_sql="SELECT * FROM employees;",
        sql_hash="dummy_hash",
        status="REJECTED",
        risk_score=100.0,
        risk_level="CRITICAL",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)
    )
    db_session.add(audit)
    db_session.commit()

    service = QueryExecutionService(db=db_session)
    with pytest.raises(QueryExecutionError, match="is REJECTED. Only 'APPROVED' queries may execute"):
        service.execute(ExecuteQueryRequest(validation_id=fake_val_id))


def test_expired_token_rejection(db_session):
    """Test 3: Token with expired TTL is rejected."""
    expired_val_id = f"val_expired_{uuid.uuid4().hex[:8]}"
    raw_sql = "SELECT id FROM departments;"
    audit = SQLValidationAuditLog(
        validation_id=expired_val_id,
        database_id="sqlite_hr_default",
        raw_sql=raw_sql,
        sanitized_sql=raw_sql,
        sql_hash=hashlib.sha256(raw_sql.encode("utf-8")).hexdigest(),
        status="APPROVED",
        risk_score=10.0,
        risk_level="LOW",
        expires_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=5)  # Expired!
    )
    db_session.add(audit)
    db_session.commit()

    service = QueryExecutionService(db=db_session)
    with pytest.raises(QueryExecutionError, match="expired"):
        service.execute(ExecuteQueryRequest(validation_id=expired_val_id))


def test_tampered_token_hash_mismatch(db_session):
    """Test 4: Token where SQL was altered after validation is rejected."""
    tampered_val_id = f"val_tampered_{uuid.uuid4().hex[:8]}"
    audit = SQLValidationAuditLog(
        validation_id=tampered_val_id,
        database_id="sqlite_hr_default",
        raw_sql="SELECT id FROM departments;",
        sanitized_sql="SELECT id FROM departments; -- altered",
        sql_hash="legit_old_hash_which_does_not_match",
        status="APPROVED",
        risk_score=10.0,
        risk_level="LOW",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)
    )
    db_session.add(audit)
    db_session.commit()

    service = QueryExecutionService(db=db_session)
    with pytest.raises(QueryExecutionError, match="Cryptographic hash mismatch"):
        service.execute(ExecuteQueryRequest(validation_id=tampered_val_id))


def test_non_existent_token_rejection(db_session):
    """Test 5: Completely fabricated token is rejected."""
    service = QueryExecutionService(db=db_session)
    with pytest.raises(QueryExecutionError, match="not found"):
        service.execute(ExecuteQueryRequest(validation_id="val_non_existent_99999"))


def test_query_result_caching(db_session):
    """Test 6: Repeated executions leverage in-memory cache unless bypassed."""
    val_id = _create_approved_token(
        db_session,
        "SELECT id, code, budget FROM departments WHERE budget > 500000;"
    )

    service = QueryExecutionService(db=db_session)
    # First execution: not cached
    res1 = service.execute(ExecuteQueryRequest(validation_id=val_id, bypass_cache=False))
    assert res1.status == "SUCCESS"
    assert res1.cached is False

    # Second execution: should hit cache!
    res2 = service.execute(ExecuteQueryRequest(validation_id=val_id, bypass_cache=False))
    assert res2.status == "SUCCESS"
    assert res2.cached is True
    assert res2.total_rows == res1.total_rows

    # Force bypass: should be fresh
    res3 = service.execute(ExecuteQueryRequest(validation_id=val_id, bypass_cache=True))
    assert res3.status == "SUCCESS"
    assert res3.cached is False


def test_pagination_handling(db_session):
    """Test 7: Pagination slices rows correctly while reporting total_rows."""
    val_id = _create_approved_token(
        db_session,
        "SELECT id, first_name, last_name FROM employees WHERE is_current = 1;"
    )

    service = QueryExecutionService(db=db_session)
    # Page 1 with page_size=5
    res = service.execute(ExecuteQueryRequest(validation_id=val_id, page=1, page_size=5, bypass_cache=True))
    assert res.status == "SUCCESS"
    assert res.total_rows >= 10
    assert len(res.rows) == 5
    assert res.page == 1
    assert res.page_size == 5


def test_cls_masking_during_execution(db_session):
    """Test 8: Sensitive columns are masked for non-PII roles during execution."""
    val_id = _create_approved_token(
        db_session,
        "SELECT first_name, last_name, email FROM employees WHERE is_current = 1 LIMIT 5;"
    )

    # Analyst user (lacks pii:view_unmasked)
    analyst_user = User(
        username=f"m8_analyst_{int(datetime.datetime.now().timestamp())}",
        full_name="M8 Analyst",
        email=f"m8_{int(datetime.datetime.now().timestamp())}@test.com",
        hashed_password="x",
        role="hr_analyst",
        is_active=True
    )
    db_session.add(analyst_user)
    db_session.commit()

    service = QueryExecutionService(db=db_session)
    res = service.execute(ExecuteQueryRequest(validation_id=val_id, bypass_cache=True), user=analyst_user)

    assert res.status == "SUCCESS"
    assert len(res.rows) > 0
    first_email = res.rows[0]["email"]
    # Should be masked e.g. "sa***@company.com"
    assert "@" in first_email
    assert "***" in first_email


def test_fastapi_execution_endpoints(client, db_session):
    """Test 9: FastAPI execution, history, cache clear, and health endpoints."""
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. First validate query to get approved token
    val_resp = client.post(
        "/api/sql-validator/validate",
        headers=headers,
        json={"sql": "SELECT id, name FROM departments;", "database_id": "sqlite_hr_default"}
    )
    val_id = val_resp.json()["validation_id"]

    # 2. Execute via API
    exec_resp = client.post(
        "/api/query-execution/execute",
        headers=headers,
        json={"validation_id": val_id, "bypass_cache": True}
    )
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    assert exec_data["status"] == "SUCCESS"
    assert exec_data["total_rows"] > 0

    # 3. Execution History endpoint
    hist_resp = client.get("/api/query-execution/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()["executions"]) >= 1

    # 4. Clear Cache endpoint
    clear_resp = client.post("/api/query-execution/cache/clear", headers=headers)
    assert clear_resp.status_code == 200
    assert "cleared" in clear_resp.json()["message"].lower()

    # 5. Health endpoint
    health_resp = client.get("/api/query-execution/health", headers=headers)
    assert health_resp.status_code == 200
    assert len(health_resp.json()["databases"]) >= 1
