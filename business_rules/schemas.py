"""Module 4: Pydantic Schemas for Business Rule Management."""

from datetime import date

from pydantic import BaseModel, Field


class RuleCreateRequest(BaseModel):
    rule_name: str = Field(..., min_length=2, description="Human-readable rule title")
    rule_type: str = Field(..., description="Category: EMPLOYEE_STATUS, EFFECTIVE_DATING, SALARY, etc.")
    rule_expression: str = Field(..., min_length=2, description="SQL filter expression e.g. employees.status = 'ACTIVE'")
    natural_language_rule: str = Field(..., min_length=5, description="Plain English description")
    description: str | None = None

    priority: str | None = Field("MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")
    mandatory: bool | None = False
    scope: str | None = Field("TABLE", description="GLOBAL, DATABASE, TABLE, COLUMN, REPORT, DEPARTMENT, ROLE")

    database_id: str | None = "sqlite_hr_default"
    table_name: str | None = None
    column_name: str | None = None

    effective_from: date | None = None
    effective_to: date | None = None

    source_type: str | None = "ADMIN_CREATED"
    source_report_id: str | None = None
    source_sql_report: str | None = None
    source_sql_expression: str | None = None
    confidence_score: float | None = 1.0


class RuleUpdateRequest(BaseModel):
    rule_name: str | None = None
    description: str | None = None
    rule_type: str | None = None
    rule_expression: str | None = None
    natural_language_rule: str | None = None
    priority: str | None = None
    mandatory: bool | None = None
    scope: str | None = None
    table_name: str | None = None
    column_name: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    change_reason: str | None = "Updated business rule configuration."


class RuleApprovalRequest(BaseModel):
    comment: str | None = Field("Confirmed and approved with HR policy.", description="Approval rationale")


class RuleRejectionRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Detailed rejection reason")


class RuleVersionCreateRequest(BaseModel):
    rule_expression: str = Field(..., min_length=2)
    natural_language_rule: str = Field(..., min_length=5)
    change_reason: str = Field(..., min_length=3)
    rule_name: str | None = None
    description: str | None = None
    rule_type: str | None = None


class RuleDependencyRequest(BaseModel):
    depends_on_rule_id: int
    dependency_type: str | None = "REQUIRES"
