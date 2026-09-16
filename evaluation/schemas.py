"""Pydantic schemas for Phase 15 Evaluation and Quality Control Framework."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TestCaseResult(BaseModel):
    test_id: str
    category: str
    question: str
    expected_tables: List[str] = []
    expected_columns: List[str] = []
    expected_business_rule: Optional[str] = None
    expected_sql: Optional[str] = None
    actual_sql: Optional[str] = None
    actual_result: Optional[Any] = None
    sql_validity: bool = False
    result_correctness: bool = False
    table_match: bool = False
    column_match: bool = False
    business_rule_match: bool = False

    # Backwards compatibility fields
    generated_sql: Optional[str] = None
    is_adversarial: bool = False
    sql_valid: bool = False
    security_passed: bool = False
    validation_status: str = "PENDING"
    execution_success: bool = False
    rag_hit: bool = False
    error_message: Optional[str] = None
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
    results: List[TestCaseResult] = []


class EvaluationRunRequest(BaseModel):
    category: Optional[str] = None
    include_adversarial: bool = True
    limit: Optional[int] = None


class AdversarialTestResult(BaseModel):
    attack_type: str
    payload: str
    blocked: bool
    blocked_by: str
    details: str
