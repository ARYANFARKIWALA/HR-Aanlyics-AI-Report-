"""Comprehensive Unit and Integration Tests for Phase 8 — Secure Query Execution Engine."""

import pytest

from backend.database.connection import SessionLocal, init_db
from query_execution.schemas import ExecuteQueryRequest
from query_execution.service import QueryExecutionError, QueryExecutionService
from sql_validator.schemas import SQLValidationRequest
from sql_validator.service import SQLValidatorService


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _get_approved_validation_id(db_session, sql: str, database_id: str = "sqlite_hr_default") -> str:
    """Helper to obtain approved validation_id from Module 7."""
    val_svc = SQLValidatorService(db=db_session)
    val_resp = val_svc.validate_query(SQLValidationRequest(
        sql=sql,
        database_id=database_id,
        user_role="admin"
    ))
    assert val_resp.status == "APPROVED"
    assert val_resp.validation_id is not None
    return val_resp.validation_id


def test_standardized_result_contract(db_session):
    """Test standardized result contract: {columns, rows, row_count, execution_time, query_id}."""
    sql = "SELECT id, name, code, budget FROM departments ORDER BY id ASC;"
    val_id = _get_approved_validation_id(db_session, sql)

    service = QueryExecutionService(db=db_session)
    req = ExecuteQueryRequest(validation_id=val_id, bypass_cache=True)
    res = service.execute(req)

    # Standardized response attributes
    assert isinstance(res.columns, list)
    assert isinstance(res.rows, list)
    assert isinstance(res.row_count, int)
    assert isinstance(res.execution_time, float)
    assert isinstance(res.query_id, str)
    assert len(res.query_id) > 0
    assert res.row_count > 0

    # to_standard_dict contract check
    std_dict = res.to_standard_dict()
    assert set(std_dict.keys()) == {"columns", "rows", "row_count", "execution_time", "query_id"}
    assert std_dict["row_count"] == len(std_dict["rows"])
    assert std_dict["columns"] == ["id", "name", "code", "budget"]


def test_execute_canonical_attrition_query(db_session):
    """Test executing the canonical monthly employee attrition query via Module 7 handshake."""
    sql = (
        "SELECT departments.name AS department, "
        "strftime('%Y-%m', employees.termination_date) AS month, "
        "COUNT(employees.id) AS attrition_count "
        "FROM employees "
        "INNER JOIN departments ON employees.department_id = departments.id "
        "WHERE employees.status = 'Terminated' "
        "AND employees.termination_date >= '2026-01-01' "
        "AND employees.termination_date <= '2026-12-31' "
        "GROUP BY departments.name, strftime('%Y-%m', employees.termination_date) "
        "ORDER BY month ASC, department ASC;"
    )
    val_id = _get_approved_validation_id(db_session, sql)

    service = QueryExecutionService(db=db_session)
    res = service.execute(ExecuteQueryRequest(validation_id=val_id, bypass_cache=True))

    assert res.status == "SUCCESS"
    assert "department" in res.columns
    assert "month" in res.columns
    assert "attrition_count" in res.columns
    assert res.execution_time >= 0


def test_never_bypass_module7(db_session):
    """Test that query execution strictly enforces Module 7 validation handshake."""
    service = QueryExecutionService(db=db_session)

    # Completely fabricated token
    with pytest.raises(QueryExecutionError, match="not found"):
        service.execute(ExecuteQueryRequest(validation_id="val_fabricated_12345"))


def test_streaming_query_execution(db_session):
    """Test streaming execution generator."""
    sql = "SELECT id, employee_number, first_name, last_name FROM employees;"
    val_id = _get_approved_validation_id(db_session, sql)

    service = QueryExecutionService(db=db_session)
    chunks = list(service.stream_query(ExecuteQueryRequest(validation_id=val_id), chunk_size=5))

    assert len(chunks) > 0
    first_chunk = chunks[0]
    assert "columns" in first_chunk
    assert "rows" in first_chunk
    assert "row_count" in first_chunk
    assert "query_id" in first_chunk
    assert first_chunk["row_count"] <= 5


def test_cancellation_tracking(db_session):
    """Test cancellation interface handles non-existent or completed queries safely."""
    res = QueryExecutionService.cancel_query("non_existent_query_id")
    assert res is False
