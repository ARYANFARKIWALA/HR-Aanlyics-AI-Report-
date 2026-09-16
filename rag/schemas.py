"""Module 5: Pydantic Schemas for RAG Knowledge Base."""

from typing import Any

from pydantic import BaseModel, Field


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language question")
    database_id: str = Field("sqlite_hr_default", description="Target database identifier")
    top_k: int | None = Field(8, ge=1, le=30, description="Number of results to retrieve")
    include_schema: bool | None = True
    include_rules: bool | None = True
    include_reports: bool | None = True


class RAGSearchHit(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    source_type: str
    chunk_type: str
    text: str
    score: float
    metadata: dict[str, Any] = {}
    why_retrieved: dict[str, Any] = {}


class RAGContextResponse(BaseModel):
    status: str = "SUCCESS"  # SUCCESS, INSUFFICIENT_CONTEXT, RULE_CONFLICT
    message: str | None = None
    query: str
    database_id: str
    database_type: str = "sqlite"

    retrieved_documents: list[dict[str, Any]] = []
    relevant_tables: list[str] = []
    relevant_columns: list[str] = []

    business_rules: list[dict[str, Any]] = []
    security_rules: list[dict[str, Any]] = []
    effective_dating_rules: list[dict[str, Any]] = []
    existing_reports: list[dict[str, Any]] = []

    context: str = ""
    retrieval_scores: list[dict[str, Any]] = []
    conflicts_detected: list[dict[str, Any]] = []


class Phase5RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language question, e.g. 'Show employee attrition by department'")
    database_id: str = Field("sqlite_hr_default", description="Target database identifier")
    top_k: int | None = Field(10, ge=1, le=50, description="Max chunks to retrieve")


class Phase5RetrievalResponse(BaseModel):
    query: str
    database_id: str
    query_understanding: dict[str, Any]
    retrieved_knowledge: list[dict[str, Any]]
    relevant_sql: list[dict[str, Any]]
    schema_tables: list[dict[str, Any]]
    business_rules: list[dict[str, Any]]
    effective_dating_rules: list[dict[str, Any]]
    glossary_definitions: list[dict[str, Any]]
    context_package: str
    total_items_retrieved: int

