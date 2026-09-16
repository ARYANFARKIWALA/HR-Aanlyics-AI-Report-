"""Module 5: Pydantic Schemas for RAG Knowledge Base."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language question")
    database_id: str = Field("sqlite_hr_default", description="Target database identifier")
    top_k: Optional[int] = Field(8, ge=1, le=30, description="Number of results to retrieve")
    include_schema: Optional[bool] = True
    include_rules: Optional[bool] = True
    include_reports: Optional[bool] = True


class RAGSearchHit(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    source_type: str
    chunk_type: str
    text: str
    score: float
    metadata: Dict[str, Any] = {}
    why_retrieved: Dict[str, Any] = {}


class RAGContextResponse(BaseModel):
    status: str = "SUCCESS"  # SUCCESS, INSUFFICIENT_CONTEXT, RULE_CONFLICT
    message: Optional[str] = None
    query: str
    database_id: str
    database_type: str = "sqlite"

    retrieved_documents: List[Dict[str, Any]] = []
    relevant_tables: List[str] = []
    relevant_columns: List[str] = []

    business_rules: List[Dict[str, Any]] = []
    security_rules: List[Dict[str, Any]] = []
    effective_dating_rules: List[Dict[str, Any]] = []
    existing_reports: List[Dict[str, Any]] = []

    context: str = ""
    retrieval_scores: List[Dict[str, Any]] = []
    conflicts_detected: List[Dict[str, Any]] = []


class Phase5RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language question, e.g. 'Show employee attrition by department'")
    database_id: str = Field("sqlite_hr_default", description="Target database identifier")
    top_k: Optional[int] = Field(10, ge=1, le=50, description="Max chunks to retrieve")


class Phase5RetrievalResponse(BaseModel):
    query: str
    database_id: str
    query_understanding: Dict[str, Any]
    retrieved_knowledge: List[Dict[str, Any]]
    relevant_sql: List[Dict[str, Any]]
    schema_tables: List[Dict[str, Any]]
    business_rules: List[Dict[str, Any]]
    effective_dating_rules: List[Dict[str, Any]]
    glossary_definitions: List[Dict[str, Any]]
    context_package: str
    total_items_retrieved: int

