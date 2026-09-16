"""Unit tests for RAG engine (Policies and SQL Repository Retrieval)."""

import pytest

from backend.database.connection import SessionLocal
from rag.embeddings import EmbeddingEngine
from rag.ingestion import DocumentIngester
from rag.retrieval import rag_retriever


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_embedding_engine_cosine_similarity():
    engine = EmbeddingEngine()
    docs = [
        "Employee attrition and voluntary turnover rates by department",
        "Salary compensation equity and compa-ratio benchmarks",
        "Parental leave and time off policy documentation"
    ]
    engine.fit(docs)

    matches = engine.find_top_k("What is the turnover in sales?", k=1)
    assert len(matches) == 1
    # Index 0 should match best
    assert matches[0][0] == 0


def test_sql_repository_semantic_retrieval(db_session):
    rag_retriever.initialize(db_session)
    matches = rag_retriever.search_sql_templates("Show attrition rates across teams", top_k=2)
    assert len(matches) > 0
    top_title = matches[0]["title"]
    assert "attrition" in top_title.lower() or "turnover" in top_title.lower()


def test_policy_rag_retrieval():
    policies = DocumentIngester.get_all_policies()
    assert len(policies) >= 5

    res = rag_retriever.answer_policy_question("What is our remote work home office stipend?")
    assert "answer" in res
    assert len(res["sources"]) > 0
