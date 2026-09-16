"""Module 6 Test Suite: AI Text-to-SQL Engine.

Tests:
1. Natural Language to SQL Translation
2. Multi-Dialect Generation (SQLite, PostgreSQL, MySQL, SQL Server, Oracle)
3. Mandatory Business Rule Enforcement
4. Row-Level Security & Role-Based Filters
5. Read-Only Safety Defense (Disallowing DDL/DML mutation)
6. Hallucination Detection (Rejecting non-existent tables/columns)
7. Ambiguity Handling & Clarification Triggers
8. Insufficient Context Enforcement (No LLM Logic Invention)
9. Plain-English SQL Explainer
10. Knowledge Traceability Mapping
11. Hard Invariant: execution_permitted is always False (Never executes SQL)
12. FastAPI Module 6 Endpoints
"""

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal, init_db
from backend.database.seeder import seed_database
from backend.main import app
from rag.rag_service import RAGService
from text_to_sql.dialect import DialectTransformer
from text_to_sql.safety import SQLSafetyValidator
from text_to_sql.schemas import TextToSQLRequest
from text_to_sql.service import TextToSQLService

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_db():
    init_db()
    seed_database()
    session = SessionLocal()
    # Ingest knowledge into RAG for sqlite_hr_default
    rag_svc = RAGService(session)
    rag_svc.ingest_database(database_id="sqlite_hr_default")
    yield session
    session.close()


def test_natural_language_to_sql_basic(setup_db):
    """Verify translating natural language question to valid read-only SQL."""
    session = setup_db
    svc = TextToSQLService(session)

    req = TextToSQLRequest(
        query="Show active headcount and average salary by department",
        database_id="sqlite_hr_default"
    )
    resp = svc.generate_sql(req)

    assert resp.status == "SUCCESS"
    assert resp.sql is not None
    assert "SELECT" in resp.sql.upper()
    assert "employees" in resp.sql.lower()
    assert "departments" in resp.sql.lower()
    assert "status = 'ACTIVE'" in resp.sql
    assert "GROUP BY" in resp.sql.upper()
    assert resp.execution_permitted is False


def test_multi_dialect_generation():
    """Verify dialect-specific transformations across engines."""
    base_sql = "SELECT employees.id, employees.salary FROM employees WHERE employees.status = 'ACTIVE'"

    # Limit / Top handling
    sql_pg = DialectTransformer.apply_limit(base_sql, 10, "postgres")
    assert "LIMIT 10" in sql_pg

    sql_tsql = DialectTransformer.apply_limit(base_sql, 10, "sqlserver")
    assert "SELECT TOP 10" in sql_tsql

    sql_ora = DialectTransformer.apply_limit(base_sql, 10, "oracle")
    assert "FETCH FIRST 10 ROWS ONLY" in sql_ora

    # Date functions
    assert DialectTransformer.get_current_date_expression("sqlite") == "DATE('now')"
    assert DialectTransformer.get_current_date_expression("postgres") == "CURRENT_DATE"
    assert DialectTransformer.get_current_date_expression("mysql") == "CURDATE()"
    assert DialectTransformer.get_current_date_expression("sqlserver") == "CAST(GETDATE() AS DATE)"
    assert DialectTransformer.get_current_date_expression("oracle") == "TRUNC(SYSDATE)"

    # String concatenation
    concat_mysql = DialectTransformer.get_concat_expression("a", "b", "mysql")
    assert "CONCAT" in concat_mysql


def test_row_level_security_filter(setup_db):
    """Verify that non-admin role injects department row-level security."""
    session = setup_db
    svc = TextToSQLService(session)

    req = TextToSQLRequest(
        query="Show active headcount by department",
        database_id="sqlite_hr_default",
        user_role="hr_manager",
        user_department="Engineering"
    )
    resp = svc.generate_sql(req)

    assert resp.status == "SUCCESS"
    assert "Engineering" in resp.sql


def test_read_only_safety_invariant():
    """Verify destructive SQL statements are blocked by safety validator."""
    destructive_queries = [
        "DROP TABLE employees",
        "DELETE FROM employees WHERE id = 1",
        "UPDATE employees SET salary = 1000000",
        "INSERT INTO employees (first_name) VALUES ('Hacker')",
        "ALTER TABLE employees ADD COLUMN ssn TEXT",
        "SELECT * FROM employees; DROP TABLE employees;"
    ]

    for q in destructive_queries:
        res = SQLSafetyValidator.validate_safety(q)
        assert res["is_safe"] is False
        assert "forbidden" in res["reason"].lower() or "multiple" in res["reason"].lower() or "must be" in res["reason"].lower()


def test_hallucination_detection():
    """Verify that referencing non-existent tables or columns is detected as hallucination."""
    allowed_tables = {"employees", "departments"}
    allowed_cols = {
        "employees": {"id", "first_name", "last_name", "salary", "status"},
        "departments": {"id", "dept_name"}
    }

    hallucinated_sql = "SELECT bitcoin_wallet, secret_code FROM cryptocurrency_accounts"
    res = SQLSafetyValidator.detect_hallucinations(
        sql=hallucinated_sql,
        allowed_tables=allowed_tables,
        allowed_columns=allowed_cols
    )

    assert res["has_hallucinations"] is True
    assert "cryptocurrency_accounts" in res["unknown_tables"]


def test_ambiguity_handling(setup_db):
    """Verify underspecified queries trigger clarification request."""
    session = setup_db
    svc = TextToSQLService(session)

    req = TextToSQLRequest(
        query="Show turnover",
        database_id="sqlite_hr_default"
    )
    resp = svc.generate_sql(req)

    assert resp.status == "AMBIGUOUS_QUERY"
    assert resp.clarification is not None
    assert len(resp.clarification.questions) > 0


def test_plain_english_explanation(setup_db):
    """Verify plain English explanation generation."""
    session = setup_db
    svc = TextToSQLService(session)

    req = TextToSQLRequest(
        query="What is the average salary by department?",
        database_id="sqlite_hr_default",
        include_explanation=True
    )
    resp = svc.generate_sql(req)

    assert resp.status == "SUCCESS"
    assert resp.explanation is not None
    assert "**Report Objective:**" in resp.explanation
    assert "**Data Sources:**" in resp.explanation


def test_knowledge_traceability_audit(setup_db):
    """Verify response includes applied rules and table/column provenance."""
    session = setup_db
    svc = TextToSQLService(session)

    req = TextToSQLRequest(
        query="Show active headcount by department",
        database_id="sqlite_hr_default"
    )
    resp = svc.generate_sql(req)

    assert resp.status == "SUCCESS"
    assert "employees" in resp.tables_used
    assert len(resp.columns_used) > 0
    assert resp.execution_permitted is False


def test_fastapi_text_to_sql_endpoints(setup_db):
    """Verify Module 6 FastAPI endpoints."""
    # 1. Generate endpoint
    gen_res = client.post("/api/text-to-sql/generate", json={
        "query": "Show active headcount by department",
        "database_id": "sqlite_hr_default"
    })
    assert gen_res.status_code == 200
    data = gen_res.json()
    assert data["status"] == "SUCCESS"
    assert "SELECT" in data["sql"]
    assert data["execution_permitted"] is False

    # 2. Plan endpoint
    plan_res = client.post("/api/text-to-sql/plan", json={
        "query": "Show active headcount by department",
        "database_id": "sqlite_hr_default"
    })
    assert plan_res.status_code == 200
    assert "target_entities" in plan_res.json()

    # 3. Explain endpoint
    explain_res = client.post("/api/text-to-sql/explain", json={
        "sql": "SELECT COUNT(*) FROM employees WHERE status = 'ACTIVE'",
        "dialect": "sqlite"
    })
    assert explain_res.status_code == 200
    assert "explanation" in explain_res.json()

    # 4. History endpoint
    hist_res = client.get("/api/text-to-sql/history")
    assert hist_res.status_code == 200
    assert isinstance(hist_res.json(), list)
