"""Phase 15: AI Evaluation Framework & Golden Dataset Verification Tests."""

import os
import json
import pytest
from backend.database.connection import SessionLocal, init_db
from evaluation.evaluator import EvaluationEngine, GOLDEN_DATASET_100_PATH, EVAL_REPORT_PATH
from evaluation.schemas import EvaluationRunRequest


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_golden_dataset_contains_at_least_100_questions():
    """Verify golden dataset contains at least 100 enterprise HR questions with all 9 required attributes."""
    dataset = EvaluationEngine.load_golden_dataset()
    assert len(dataset) >= 100, f"Expected at least 100 questions, got {len(dataset)}"

    required_keys = [
        "question",
        "expected_tables",
        "expected_columns",
        "expected_business_rule",
        "expected_sql",
        "actual_sql",
        "actual_result",
        "sql_validity",
        "result_correctness"
    ]

    for tc in dataset:
        for key in required_keys:
            assert key in tc, f"Test case {tc.get('id')} missing required key '{key}'"
        assert isinstance(tc["question"], str) and len(tc["question"]) > 5
        assert isinstance(tc["expected_tables"], list)


def test_evaluation_benchmark_calculates_all_8_metrics(db_session):
    """Verify execution of evaluation framework and calculation of all 8 empirical metrics."""
    # Execute full benchmark across all questions in golden dataset
    summary = EvaluationEngine.run_benchmark(db=db_session)

    assert summary.total_cases >= 100

    # 1. SQL execution success rate
    assert summary.sql_execution_success_rate >= 90.0, f"Low execution success: {summary.sql_execution_success_rate}%"

    # 2. SQL correctness
    assert summary.sql_correctness >= 90.0, f"Low SQL correctness: {summary.sql_correctness}%"

    # 3. Table selection accuracy
    assert summary.table_selection_accuracy >= 90.0, f"Low table accuracy: {summary.table_selection_accuracy}%"

    # 4. Column selection accuracy
    assert summary.column_selection_accuracy >= 90.0, f"Low column accuracy: {summary.column_selection_accuracy}%"

    # 5. RAG retrieval accuracy
    assert summary.rag_retrieval_accuracy >= 80.0, f"Low RAG accuracy: {summary.rag_retrieval_accuracy}%"

    # 6. Business rule accuracy
    assert summary.business_rule_accuracy >= 85.0, f"Low business rule accuracy: {summary.business_rule_accuracy}%"

    # 7. Result accuracy
    assert summary.result_accuracy >= 90.0, f"Low result accuracy: {summary.result_accuracy}%"

    # 8. Average latency
    assert summary.average_latency > 0.0
    assert summary.average_latency < 500.0, f"High average latency: {summary.average_latency}ms"

    # Adversarial security defense rate must be 100%
    assert summary.security_defense_rate == 100.0

    # Verify markdown evaluation report generated
    assert os.path.exists(EVAL_REPORT_PATH)
    with open(EVAL_REPORT_PATH, "r", encoding="utf-8") as f:
        report_content = f.read()
    assert "SQL Execution Success Rate" in report_content
    assert "Average Latency" in report_content
    assert "Adversarial Security Defense" in report_content
