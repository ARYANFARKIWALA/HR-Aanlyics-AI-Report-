"""Module 6: Pydantic Schemas for AI Text-to-SQL Engine."""

from typing import Any

from pydantic import BaseModel, Field


class TextToSQLRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language reporting question")
    database_id: str = Field("sqlite_hr_default", description="Target database connection ID")
    target_dialect: str | None = Field(None, description="Optional target database dialect (e.g. sqlite, postgres, mysql, sqlserver, oracle)")
    user_role: str = Field("admin", description="Security role of the user (e.g. admin, hr_manager, employee)")
    user_department: str | None = Field(None, description="Department of the user for row-level security")
    date_context: str | None = Field(None, description="Temporal reference date (e.g. '2026-01-01', 'current')")
    include_explanation: bool = Field(True, description="Whether to include plain English translation")
    include_plan: bool = Field(True, description="Whether to include structured query execution plan")


class QueryPlan(BaseModel):
    intent: str
    target_entities: list[str] = []
    metrics: list[str] = []
    dimensions: list[str] = []
    group_by: list[str] = []
    order_by: list[str] = []
    filters: list[str] = []
    joins: list[str] = []
    effective_date_strategy: str | None = None
    applied_rule_ids: list[int] = []
    reused_report_id: int | None = None
    limit: int | None = None


class ClarificationRequest(BaseModel):
    is_ambiguous: bool = False
    ambiguity_type: str | None = None  # TEMPORAL, METRIC_DEFINITION, ENTITY_RESOLUTION, UNRESOLVED_SCHEMA_ENTITY
    questions: list[str] = []
    suggested_queries: list[str] = []


class ReasoningMetadata(BaseModel):
    """Structured audit reasoning without exposing hidden chain-of-thought tokens."""
    intent_summary: str
    target_dialect: str
    entities_identified: list[str] = []
    metrics_identified: list[str] = []
    dimensions_identified: list[str] = []
    filters_applied: list[str] = []
    applied_business_rules: list[str] = []
    confidence_score: float = 1.0


class TextToSQLResponse(BaseModel):
    status: str = "SUCCESS"  # SUCCESS, INSUFFICIENT_CONTEXT, BLOCKED_BY_SAFETY, AMBIGUOUS_QUERY, CLARIFICATION_REQUIRED, SYNTAX_ERROR
    message: str | None = None
    sql: str | None = None
    dialect: str = "sqlite"
    database_id: str = "sqlite_hr_default"
    explanation: str | None = None
    query_plan: dict[str, Any] | None = None
    clarification: ClarificationRequest | None = None
    reasoning_metadata: ReasoningMetadata | None = None
    applied_rules: list[dict[str, Any]] = []
    reused_reports: list[dict[str, Any]] = []
    tables_used: list[str] = []
    columns_used: list[str] = []
    warnings: list[str] = []
    execution_permitted: bool = False  # Hard invariant: Text-to-SQL never executes SQL
    confidence_score: float = 1.0
