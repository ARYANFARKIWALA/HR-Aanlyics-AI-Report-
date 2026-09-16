"""Pydantic schemas for Phase 15 Evaluation and Quality Control Framework."""

from typing import Any

from pydantic import BaseModel


class TestCaseResult(BaseModel):
    test_id: str
    category: str
    question: str
    expected_tables: list[str] = []
    expected_columns: list[str] = []
    expected_business_rule: str | None = None
    expected_sql: str | None = None
    actual_sql: str | None = None
    actual_result: Any | None = None
    sql_validity: bool = False
    result_correctness: bool = False
    table_match: bool = False
    column_match: bool = False
    business_rule_match: bool = False

    # Backwards compatibility fields
    generated_sql: str | None = None
    is_adversarial: bool = False
    sql_valid: bool = False
    security_passed: bool = False
    validation_status: str = "PENDING"
    execution_success: bool = False
    rag_hit: bool = False
    error_message: str | None = None
    latency_ms: float = 0.0


class EvaluationSummary(BaseModel):
    total_cases: int
    passed_cases: int

    # Exact Phase 15 8 Required Metrics
    sql_execution_success_rate: float
    sql_correctness: float
    table_selection_accuracy: float
    column_selection_accuracy: float
    rag_retrieval_accuracy: float
    business_rule_accuracy: float
    result_accuracy: float
    average_latency: float

    # Legacy compatibility fields
    sql_validity_rate: float
    execution_accuracy_rate: float
    security_defense_rate: float
    rag_hit_rate: float
    avg_latency_ms: float

    timestamp: str
    results: list[TestCaseResult] = []


class EvaluationRunRequest(BaseModel):
    category: str | None = None
    include_adversarial: bool = True
    limit: int | None = None


class AdversarialTestResult(BaseModel):
    attack_type: str
    payload: str
    blocked: bool
    blocked_by: str
    details: str
