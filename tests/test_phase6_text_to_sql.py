"""Comprehensive Unit and Integration Tests for Phase 6 — AI Text-to-SQL Engine."""

import pytest

from backend.database.connection import SessionLocal, init_db
from text_to_sql.schemas import TextToSQLRequest
from text_to_sql.service import TextToSQLService


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_canonical_attrition_query(db_session):
    """Test canonical query: 'Show monthly employee attrition by department for 2026.'"""
    service = TextToSQLService(db=db_session)
    request = TextToSQLRequest(
        query="Show monthly employee attrition by department for 2026.",
        database_id="sqlite_hr_default",
        user_role="admin",
        include_explanation=True,
        include_plan=True
    )
    res = service.generate_sql(request)

    assert res.status == "SUCCESS"
    assert res.execution_permitted is False  # Hard invariant: Text-to-SQL never executes SQL
    assert res.sql is not None
    assert "employees" in res.tables_used
    assert "departments" in res.tables_used
    assert "attrition_count" in res.sql
    assert "2026-01-01" in res.sql
    assert "2026-12-31" in res.sql
    assert res.explanation is not None
    assert res.reasoning_metadata is not None
    assert res.reasoning_metadata.target_dialect == "sqlite"
    assert len(res.reasoning_metadata.entities_identified) > 0


def test_dialect_transpilation_postgresql(db_session):
    """Test transpilation to PostgreSQL dialect."""
    service = TextToSQLService(db=db_session)
    request = TextToSQLRequest(
        query="Show monthly employee attrition by department for 2026.",
        target_dialect="postgres",
        user_role="admin"
    )
    res = service.generate_sql(request)

    assert res.status == "SUCCESS"
    assert res.dialect == "postgres"
    assert res.sql is not None
    assert res.execution_permitted is False


def test_dialect_transpilation_mysql(db_session):
    """Test transpilation to MySQL dialect."""
    service = TextToSQLService(db=db_session)
    request = TextToSQLRequest(
        query="Show monthly employee attrition by department for 2026.",
        target_dialect="mysql",
        user_role="admin"
    )
    res = service.generate_sql(request)

    assert res.status == "SUCCESS"
    assert res.dialect == "mysql"
    assert res.sql is not None
    assert res.execution_permitted is False


def test_dialect_transpilation_tsql(db_session):
    """Test transpilation to T-SQL (SQL Server) dialect."""
    service = TextToSQLService(db=db_session)
    request = TextToSQLRequest(
        query="Show top 5 employee headcount by department",
        target_dialect="tsql",
        user_role="admin"
    )
    res = service.generate_sql(request)

    assert res.status == "SUCCESS"
    assert res.dialect == "tsql"
    assert res.sql is not None
    assert res.execution_permitted is False


def test_dialect_transpilation_oracle(db_session):
    """Test transpilation to Oracle dialect."""
    service = TextToSQLService(db=db_session)
    request = TextToSQLRequest(
        query="Show top 5 employee headcount by department",
        target_dialect="oracle",
        user_role="admin"
    )
    res = service.generate_sql(request)

    assert res.status == "SUCCESS"
    assert res.dialect == "oracle"
    assert res.sql is not None
    assert res.execution_permitted is False


def test_anti_hallucination_unresolved_entity(db_session):
    """Test anti-hallucination defense returning CLARIFICATION_REQUIRED for non-HR entities."""
    service = TextToSQLService(db=db_session)
    request = TextToSQLRequest(
        query="Show employee shoe size and bitcoin balance",
        user_role="admin"
    )
    res = service.generate_sql(request)

    assert res.status == "CLARIFICATION_REQUIRED"
    assert res.clarification is not None
    assert res.clarification.is_ambiguous is True
    assert res.clarification.ambiguity_type == "UNRESOLVED_SCHEMA_ENTITY"
    assert len(res.clarification.questions) > 0
    assert len(res.clarification.suggested_queries) > 0


def test_plan_only_mode(db_session):
    """Test plan_only endpoint returns structured QueryPlan dictionary."""
    service = TextToSQLService(db=db_session)
    request = TextToSQLRequest(
        query="Show employee headcount by department",
        user_role="admin"
    )
    plan_dict = service.plan_only(request)

    assert "target_entities" in plan_dict
    assert "metrics" in plan_dict
    assert "dimensions" in plan_dict
    assert "employees" in plan_dict["target_entities"]
