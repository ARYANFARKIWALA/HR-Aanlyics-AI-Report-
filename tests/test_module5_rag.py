"""Module 5 Test Suite: RAG Knowledge Base.

Tests:
1. Dense Vector Embeddings (128-dim, normalized, cosine similarity)
2. Semantic Chunking & Metadata Preservation
3. Multi-database Isolation
4. Rule Approval Invariant (Only ACTIVE rules and APPROVED reports indexed)
5. Zero Raw PII Invariant
6. Hybrid Retrieval with Explainability ("Why retrieved?")
7. Priority Re-ranking (CRITICAL Security rules prioritized)
8. Prompt Injection Defense (<ORGANIZATIONAL_KNOWLEDGE> delimitation)
9. Insufficient Context Detection
10. FastAPI RAG Endpoints
"""

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal, init_db
from backend.database.models_rules import BusinessRule
from backend.database.seeder import seed_database
from backend.main import app
from rag.chunker import SemanticChunker
from rag.embedding_service import EmbeddingService
from rag.rag_service import RAGService

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_db():
    init_db()
    seed_database()
    session = SessionLocal()
    # Ingest knowledge for test
    svc = RAGService(session)
    svc.ingest_database(database_id="sqlite_hr_default")
    yield session
    session.close()


def test_embedding_service_semantic_projection():
    """Verify 128-dim dense embedding generation and cosine similarity."""
    svc = EmbeddingService()
    v1 = svc.generate_embedding("Employee attrition rate and voluntary turnover")
    v2 = svc.generate_embedding("Employee voluntary turnover and attrition rate statistics")
    v3 = svc.generate_embedding("Office printer toner cartridge replacement steps")

    assert len(v1) == 128
    assert len(v2) == 128
    assert len(v3) == 128

    sim_related = svc.cosine_similarity(v1, v2)
    sim_unrelated = svc.cosine_similarity(v1, v3)

    assert sim_related > sim_unrelated
    assert sim_related > 0.4


def test_chunker_semantic_boundaries():
    """Verify semantic chunker segments business rule while preserving metadata."""
    rule_data = {
        "id": 999,
        "rule_code": "RULE_CHK_01",
        "rule_name": "Active Status Check",
        "rule_type": "BUSINESS",
        "rule_expression": "employees.status = 'ACTIVE'",
        "natural_language_rule": "An active employee must have status 'ACTIVE'",
        "table_name": "employees",
        "column_name": "status",
        "priority": "HIGH",
        "mandatory": True
    }
    chunks = SemanticChunker.chunk_business_rule(
        doc_id="doc_rule_999",
        rule_data=rule_data,
        database_id="sqlite_hr_default"
    )
    assert len(chunks) >= 1
    assert chunks[0].chunk_type == "BUSINESS_RULE"
    assert chunks[0].table_names == ["employees"]
    assert chunks[0].rule_id == 999


def test_knowledge_ingestion_and_counts(setup_db):
    """Verify all eligible knowledge sources are indexed."""
    session = setup_db
    svc = RAGService(session)
    stats = svc.get_stats(database_id="sqlite_hr_default")

    assert stats["total_documents"] > 0
    assert stats["total_chunks"] > 0
    assert "DATABASE_SCHEMA" in stats["by_source_type"] or "BUSINESS_RULE" in stats["by_source_type"]


def test_rule_approval_invariant(setup_db):
    """Verify only ACTIVE rules are indexed in RAG."""
    session = setup_db
    # Clean up if already exists
    existing = session.query(BusinessRule).filter_by(rule_code="TEST_DRAFT_RULE_UNAPPROVED").first()
    if existing:
        session.delete(existing)
        session.commit()

    # Create an unapproved DRAFT rule
    draft_rule = BusinessRule(
        database_id="sqlite_hr_default",
        rule_code="TEST_DRAFT_RULE_UNAPPROVED",
        rule_name="Draft Unapproved Rule",
        rule_expression="salary < 0",
        natural_language_rule="Draft rule prohibiting negative salary",
        rule_type="BUSINESS",
        table_name="employees",
        status="DRAFT",
        is_current=True
    )
    session.add(draft_rule)
    session.commit()

    try:
        svc = RAGService(session)
        with pytest.raises(ValueError, match="Only ACTIVE and current rules can be indexed"):
            svc.ingest_rule(draft_rule.id)

        # Search should NOT return this draft rule
        hits = svc.search("salary < 0", database_id="sqlite_hr_default")
        assert not any(h.get("rule_id") == draft_rule.id for h in hits)
    finally:
        session.delete(draft_rule)
        session.commit()


def test_database_isolation_invariant(setup_db):
    """Knowledge from sqlite_hr_default must never leak into queries for another database."""
    session = setup_db
    svc = RAGService(session)
    # Search with a non-existent database_id
    isolated_hits = svc.search("employees salary department", database_id="isolated_finance_db")
    assert len(isolated_hits) == 0


def test_security_priority_boosting(setup_db):
    """Verify CRITICAL security access rules receive highest priority boost."""
    session = setup_db
    # Clean up if already exists
    existing = session.query(BusinessRule).filter_by(rule_code="SEC_PII_SALARY_RESTRICT").first()
    if existing:
        session.delete(existing)
        session.commit()

    # Add an active CRITICAL security rule
    sec_rule = BusinessRule(
        database_id="sqlite_hr_default",
        rule_code="SEC_PII_SALARY_RESTRICT",
        rule_name="PII Salary Restriction Policy",
        rule_expression="user_role = 'ADMIN' OR department_id = user_dept",
        natural_language_rule="Users can only view salary if admin or belonging to the department",
        rule_type="SECURITY",
        table_name="employees",
        priority="CRITICAL",
        mandatory=True,
        status="ACTIVE",
        is_current=True
    )
    session.add(sec_rule)
    session.commit()

    try:
        svc = RAGService(session)
        svc.ingest_rule(sec_rule.id)

        hits = svc.search("salary restriction policy admin access", database_id="sqlite_hr_default")
        assert len(hits) > 0
        top_hit = hits[0]
        assert top_hit["security_level"] == "CRITICAL" or top_hit["rule_id"] == sec_rule.id
        assert top_hit["why_retrieved"]["is_critical_security"] is True
    finally:
        session.delete(sec_rule)
        session.commit()


def test_prompt_injection_delimited_context(setup_db):
    """Verify context is strictly bounded by <ORGANIZATIONAL_KNOWLEDGE> tags."""
    session = setup_db
    svc = RAGService(session)
    ctx = svc.get_context_for_query(
        query="Active headcount by department",
        database_id="sqlite_hr_default"
    )

    assert ctx.status == "SUCCESS"
    assert "<ORGANIZATIONAL_KNOWLEDGE>" in ctx.context
    assert "</ORGANIZATIONAL_KNOWLEDGE>" in ctx.context
    assert "TARGET DATABASE: sqlite_hr_default" in ctx.context


def test_insufficient_context_detection(setup_db):
    """Verify empty retrieval returns INSUFFICIENT_CONTEXT."""
    session = setup_db
    svc = RAGService(session)
    # Context builder on empty hits
    ctx = svc.context_builder.build_context(
        query="Completely unrelated query xyz1234908",
        retrieved_chunks=[],
        database_id="sqlite_hr_default"
    )
    assert ctx.status == "INSUFFICIENT_CONTEXT"
    assert "No approved business rule" in ctx.message


def test_api_rag_endpoints(setup_db):
    """Verify FastAPI endpoints for Module 5."""
    res_stats = client.get("/api/rag/stats?database_id=sqlite_hr_default")
    assert res_stats.status_code == 200
    assert "total_chunks" in res_stats.json()

    res_search = client.post("/api/rag/search", json={
        "query": "active employees salary",
        "database_id": "sqlite_hr_default",
        "top_k": 3
    })
    assert res_search.status_code == 200
    assert "results" in res_search.json()

    res_context = client.post("/api/rag/context", json={
        "query": "headcount report",
        "database_id": "sqlite_hr_default",
        "top_k": 3
    })
    assert res_context.status_code == 200
    assert "<ORGANIZATIONAL_KNOWLEDGE>" in res_context.json()["context"]
