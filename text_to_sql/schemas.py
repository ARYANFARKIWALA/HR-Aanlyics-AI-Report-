"""Module 6: Pydantic Schemas for AI Text-to-SQL Engine."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TextToSQLRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language reporting question")
    database_id: str = Field("sqlite_hr_default", description="Target database connection ID")
    target_dialect: Optional[str] = Field(None, description="Optional target database dialect (e.g. sqlite, postgres, mysql, sqlserver, oracle)")
    user_role: str = Field("admin", description="Security role of the user (e.g. admin, hr_manager, employee)")
    user_department: Optional[str] = Field(None, description="Department of the user for row-level security")
    date_context: Optional[str] = Field(None, description="Temporal reference date (e.g. '2026-01-01', 'current')")
    include_explanation: bool = Field(True, description="Whether to include plain English translation")
    include_plan: bool = Field(True, description="Whether to include structured query execution plan")


class QueryPlan(BaseModel):
    intent: str
    target_entities: List[str] = []
    metrics: List[str] = []
    dimensions: List[str] = []
    group_by: List[str] = []
    order_by: List[str] = []
    filters: List[str] = []
    joins: List[str] = []
    effective_date_strategy: Optional[str] = None
    applied_rule_ids: List[int] = []
    reused_report_id: Optional[int] = None
    limit: Optional[int] = None


class ClarificationRequest(BaseModel):
    is_ambiguous: bool = False
    ambiguity_type: Optional[str] = None  # TEMPORAL, METRIC_DEFINITION, ENTITY_RESOLUTION, UNRESOLVED_SCHEMA_ENTITY
    questions: List[str] = []
    suggested_queries: List[str] = []


class ReasoningMetadata(BaseModel):
    """Structured audit reasoning without exposing hidden chain-of-thought tokens."""
    intent_summary: str
    target_dialect: str
    entities_identified: List[str] = []
    metrics_identified: List[str] = []
    dimensions_identified: List[str] = []
    filters_applied: List[str] = []
    applied_business_rules: List[str] = []
    confidence_score: float = 1.0


class TextToSQLResponse(BaseModel):
    status: str = "SUCCESS"  # SUCCESS, INSUFFICIENT_CONTEXT, BLOCKED_BY_SAFETY, AMBIGUOUS_QUERY, CLARIFICATION_REQUIRED, SYNTAX_ERROR
    message: Optional[str] = None
    sql: Optional[str] = None
    dialect: str = "sqlite"
    database_id: str = "sqlite_hr_default"
    explanation: Optional[str] = None
    query_plan: Optional[Dict[str, Any]] = None
    clarification: Optional[ClarificationRequest] = None
    reasoning_metadata: Optional[ReasoningMetadata] = None
    applied_rules: List[Dict[str, Any]] = []
    reused_reports: List[Dict[str, Any]] = []
    tables_used: List[str] = []
    columns_used: List[str] = []
    warnings: List[str] = []
    execution_permitted: bool = False  # Hard invariant: Text-to-SQL never executes SQL
    confidence_score: float = 1.0
