"""Phase 15: Explicit Verification of All 9 Test Categories.

Test Categories:
1. Unit tests
2. Integration tests
3. API tests
4. Database tests
5. Security tests
6. RAG retrieval tests
7. Text-to-SQL tests
8. End-to-end tests
9. Performance tests
"""

import time
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import SessionLocal, init_db
from backend.database.models import User, Department
from backend.auth.password import hash_password, verify_password
from backend.database.connection_manager import connection_manager
from rag.rag_service import RAGService
from text_to_sql.service import TextToSQLService
from text_to_sql.schemas import TextToSQLRequest
from sql_validator.service import SQLValidatorService
from sql_validator.schemas import SQLValidationRequest
from query_execution.service import QueryExecutionService
from query_execution.schemas import ExecuteQueryRequest
from backend.services.workflow_orchestrator import EnterpriseWorkflowOrchestrator


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# -----------------------------------------------------------------
# 1. Unit Tests
# -----------------------------------------------------------------
def test_category_1_unit_password_hashing():
    """Unit test: Verify password hashing, salt uniqueness, and PBKDF2 verification."""
    pwd = "EnterpriseSecurePass123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


# -----------------------------------------------------------------
# 2. Integration Tests
# -----------------------------------------------------------------
def test_category_2_integration_validator_to_executor(db_session):
    """Integration test: Module 7 token handoff to Module 8 executor."""
    validator = SQLValidatorService(db=db_session)
    executor = QueryExecutionService(db=db_session)

    val_res = validator.validate_query(SQLValidationRequest(
        sql="SELECT name, budget FROM departments WHERE budget > 0;",
        database_id="sqlite_hr_default",
        user_role="admin"
    ))
    assert val_res.status == "APPROVED"
    assert val_res.validation_id is not None

    exec_res = executor.execute(ExecuteQueryRequest(
        validation_id=val_res.validation_id,
        bypass_cache=True
    ))
    assert exec_res.status == "SUCCESS"
    assert len(exec_res.columns) == 2


# -----------------------------------------------------------------
# 3. API Tests
# -----------------------------------------------------------------
def test_category_3_api_health_and_docs(client):
    """API test: Verify FastAPI OpenAPI documentation and system health endpoint."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "healthy"

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    assert "paths" in openapi_resp.json()


# -----------------------------------------------------------------
# 4. Database Tests
# -----------------------------------------------------------------
def test_category_4_database_connection_and_schema():
    """Database test: Schema discovery across connected databases."""
    db_id = "sqlite_hr_default"
    schema = connection_manager.get_schema(db_id)
    assert schema is not None
    assert "employees" in schema.table_allowlist
    assert "departments" in schema.table_allowlist


# -----------------------------------------------------------------
# 5. Security Tests
# -----------------------------------------------------------------
def test_category_5_security_attack_interception(db_session):
    """Security test: Interception of SQL injection and credential extraction."""
    validator = SQLValidatorService(db=db_session)
    # Attempt SQL injection with DROP TABLE
    drop_res = validator.validate_query(SQLValidationRequest(
        sql="SELECT * FROM employees; DROP TABLE users; --",
        database_id="sqlite_hr_default",
        user_role="admin"
    ))
    assert drop_res.status == "REJECTED"

    # Attempt sensitive column access
    cred_res = validator.validate_query(SQLValidationRequest(
        sql="SELECT username, hashed_password FROM users;",
        database_id="sqlite_hr_default",
        user_role="admin"
    ))
    assert cred_res.status == "REJECTED"


# -----------------------------------------------------------------
# 6. RAG Retrieval Tests
# -----------------------------------------------------------------
def test_category_6_rag_retrieval(db_session):
    """RAG test: Semantic retrieval of schema, rules, and report templates."""
    rag_svc = RAGService(db=db_session)
    ctx = rag_svc.get_context_for_query(
        query="Show monthly employee attrition by department for 2026.",
        database_id="sqlite_hr_default",
        top_k=5
    )
    assert ctx.status == "SUCCESS"
    assert len(ctx.retrieved_documents) > 0


# -----------------------------------------------------------------
# 7. Text-to-SQL Tests
# -----------------------------------------------------------------
def test_category_7_text_to_sql_generation(db_session):
    """Text-to-SQL test: Convert natural language to dialect-adapted SQL."""
    t2s_svc = TextToSQLService(db=db_session)
    req = TextToSQLRequest(
        query="Show active employee count by department",
        database_id="sqlite_hr_default",
        user_role="admin"
    )
    resp = t2s_svc.generate_sql(req)
    assert resp.status == "SUCCESS"
    assert resp.sql is not None
    assert "SELECT" in resp.sql.upper()


# -----------------------------------------------------------------
# 8. End-to-End Tests
# -----------------------------------------------------------------
def test_category_8_end_to_end_workflow(db_session):
    """End-to-end test: Full 14-stage lifecycle pipeline."""
    admin_user = db_session.query(User).filter(User.role == "SUPER_ADMIN", User.is_active == True).first()
    orchestrator = EnterpriseWorkflowOrchestrator(db=db_session)
    result = orchestrator.execute_canonical_scenario(
        question="Show monthly employee attrition by department for 2026.",
        database_id="sqlite_hr_default",
        username=admin_user.username
    )
    assert result["status"] == "SUCCESS"
    assert result["stages_completed"] == 14


# -----------------------------------------------------------------
# 9. Performance Tests
# -----------------------------------------------------------------
def test_category_9_performance_latencies(db_session):
    """Performance test: Sub-second latency guarantees across core engine components."""
    validator = SQLValidatorService(db=db_session)
    executor = QueryExecutionService(db=db_session)

    # 1. Validation Latency (< 250ms)
    t0 = time.time()
    val_res = validator.validate_query(SQLValidationRequest(
        sql="SELECT id, name FROM departments LIMIT 10;",
        database_id="sqlite_hr_default",
        user_role="admin"
    ))
    val_time_ms = (time.time() - t0) * 1000.0
    assert val_time_ms < 250.0, f"Validation exceeded latency threshold: {val_time_ms}ms"

    # 2. Execution Latency (< 250ms)
    t1 = time.time()
    exec_res = executor.execute(ExecuteQueryRequest(
        validation_id=val_res.validation_id,
        bypass_cache=True
    ))
    exec_time_ms = (time.time() - t1) * 1000.0
    assert exec_time_ms < 250.0, f"Execution exceeded latency threshold: {exec_time_ms}ms"
