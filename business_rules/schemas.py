"""Module 4: Pydantic Schemas for Business Rule Management."""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field


class RuleCreateRequest(BaseModel):
    rule_name: str = Field(..., min_length=2, description="Human-readable rule title")
    rule_type: str = Field(..., description="Category: EMPLOYEE_STATUS, EFFECTIVE_DATING, SALARY, etc.")
    rule_expression: str = Field(..., min_length=2, description="SQL filter expression e.g. employees.status = 'ACTIVE'")
    natural_language_rule: str = Field(..., min_length=5, description="Plain English description")
    description: Optional[str] = None

    priority: Optional[str] = Field("MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")
    mandatory: Optional[bool] = False
    scope: Optional[str] = Field("TABLE", description="GLOBAL, DATABASE, TABLE, COLUMN, REPORT, DEPARTMENT, ROLE")

    database_id: Optional[str] = "sqlite_hr_default"
    table_name: Optional[str] = None
    column_name: Optional[str] = None

    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

    source_type: Optional[str] = "ADMIN_CREATED"
    source_report_id: Optional[str] = None
    source_sql_report: Optional[str] = None
    source_sql_expression: Optional[str] = None
    confidence_score: Optional[float] = 1.0


class RuleUpdateRequest(BaseModel):
    rule_name: Optional[str] = None
    description: Optional[str] = None
    rule_type: Optional[str] = None
    rule_expression: Optional[str] = None
    natural_language_rule: Optional[str] = None
    priority: Optional[str] = None
    mandatory: Optional[bool] = None
    scope: Optional[str] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    change_reason: Optional[str] = "Updated business rule configuration."


class RuleApprovalRequest(BaseModel):
    comment: Optional[str] = Field("Confirmed and approved with HR policy.", description="Approval rationale")


class RuleRejectionRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Detailed rejection reason")


class RuleVersionCreateRequest(BaseModel):
    rule_expression: str = Field(..., min_length=2)
    natural_language_rule: str = Field(..., min_length=5)
    change_reason: str = Field(..., min_length=3)
    rule_name: Optional[str] = None
    description: Optional[str] = None
    rule_type: Optional[str] = None


class RuleDependencyRequest(BaseModel):
    depends_on_rule_id: int
    dependency_type: Optional[str] = "REQUIRES"
