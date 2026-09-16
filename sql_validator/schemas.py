"""Pydantic schemas and data models for Module 7 - SQL Validator & Security Engine."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChecklistItem(BaseModel):
    check_name: str
    passed: bool
    severity: str = "BLOCKER"  # BLOCKER, WARNING, INFO
    details: str = ""


class ComplexityMetrics(BaseModel):
    table_count: int = 0
    join_count: int = 0
    subquery_count: int = 0
    aggregation_count: int = 0
    has_group_by: bool = False
    has_order_by: bool = False
    has_window_functions: bool = False
    estimated_complexity_score: float = 0.0


class SQLValidationRequest(BaseModel):
    sql: str
    database_id: str = "sqlite_hr_default"
    user_id: Optional[int] = None
    username: Optional[str] = "admin"
    user_role: Optional[str] = "admin"
    department_id: Optional[int] = None
    allow_select_star: bool = False


class SQLValidationResponse(BaseModel):
    validation_id: Optional[str] = None
    status: str  # APPROVED (VALID), REJECTED, REQUIRES_APPROVAL
    is_valid: bool = False
    safe_error_explanation: Optional[str] = None
    risk_score: float
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    sanitized_sql: str
    sql_hash: str
    expires_at: Optional[str] = None
    checklist: List[ChecklistItem] = []
    violations: List[str] = []
    warnings: List[str] = []
    complexity_metrics: ComplexityMetrics = Field(default_factory=ComplexityMetrics)
    can_execute: bool = False  # Hard invariant: True ONLY if status == 'APPROVED'
    timeout_seconds: int = 30
    max_row_limit: int = 5000


class ValidationPolicy(BaseModel):
    allow_select_star: bool = False
    max_joins: int = 5
    disallow_cartesian: bool = True
    disallow_comments: bool = True
    require_where_on_large_tables: bool = True
    large_table_threshold_rows: int = 1000
    max_risk_score_auto_approval: float = 65.0
    token_ttl_minutes: int = 15
