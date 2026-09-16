"""Unit and Integration Tests for Module 13 — Testing, Evaluation & AI Quality Control."""

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal, init_db
from backend.main import app
from evaluation.adversarial_runner import AdversarialSecurityRunner
from evaluation.evaluator import EvaluationEngine
from evaluation.schemas import EvaluationRunRequest


@pytest.fixture(scope="function")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_golden_dataset_structure():
    """Test 1: Golden benchmark dataset loads with valid enterprise test schemas."""
    dataset = EvaluationEngine.load_golden_dataset()
    assert len(dataset) >= 8

    required_keys = {"id", "category", "question", "expected_tables", "expected_status", "is_adversarial"}
    has_adversarial = False
    has_standard = False

    for tc in dataset:
        for k in required_keys:
            assert k in tc, f"Test case {tc.get('id')} missing key '{k}'"

        if tc["is_adversarial"]:
            has_adversarial = True
            assert tc["expected_status"] == "REJECTED"
        else:
            has_standard = True
            assert tc["expected_status"] == "APPROVED"

    assert has_adversarial, "Dataset must contain adversarial test cases"
    assert has_standard, "Dataset must contain standard reporting test cases"


def test_evaluation_benchmark_execution(db_session):
    """Test 2: EvaluationEngine executes benchmark and calculates quality KPIs."""
    summary = EvaluationEngine.run_benchmark(db=db_session)

    assert summary.total_cases >= 8
    assert summary.sql_validity_rate >= 80.0
    assert summary.execution_accuracy_rate >= 80.0
    assert summary.security_defense_rate == 100.0  # Zero compromises on adversarial tests
    assert summary.avg_latency_ms >= 0.0
    assert len(summary.results) == summary.total_cases

    # Verify latest summary caching
    cached = EvaluationEngine.get_latest_summary()
    assert cached is not None
    assert cached.total_cases == summary.total_cases


def test_evaluation_filtered_category(db_session):
    """Test 3: Benchmark runner correctly filters by domain category."""
    req = EvaluationRunRequest(category="Headcount", include_adversarial=False)
    summary = EvaluationEngine.run_benchmark(db=db_session, req=req)

    assert summary.total_cases >= 1
    for r in summary.results:
        assert r.category == "Headcount"
        assert r.is_adversarial is False


def test_adversarial_penetration_suite(db_session):
    """Test 4: Adversarial runner executes 7 penetration vectors with 100% defense rate."""
    results = AdversarialSecurityRunner.run_penetration_tests(db=db_session)
    assert len(results) >= 7

    for res in results:
        assert res.blocked is True, f"Attack vector '{res.attack_type}' was not blocked: {res.payload}"
        assert "Zero-Trust" in res.blocked_by


def test_fastapi_evaluation_endpoints(client, db_session):
    """Test 5: FastAPI evaluation, scorecard, dataset, and adversarial test routes."""
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Inspect golden dataset
    ds_resp = client.get("/api/evaluation/golden-dataset", headers=headers)
    assert ds_resp.status_code == 200
    assert len(ds_resp.json()) >= 8

    # 2. Run benchmark via API
    run_resp = client.post(
        "/api/evaluation/run",
        headers=headers,
        json={"include_adversarial": True}
    )
    assert run_resp.status_code == 200
    summary = run_resp.json()
    assert summary["total_cases"] >= 8
    assert summary["security_defense_rate"] == 100.0

    # 3. Get latest evaluation
    latest_resp = client.get("/api/evaluation/latest", headers=headers)
    assert latest_resp.status_code == 200
    assert latest_resp.json()["total_cases"] == summary["total_cases"]

    # 4. Run adversarial stress tests via API
    adv_resp = client.post("/api/evaluation/adversarial", headers=headers)
    assert adv_resp.status_code == 200
    adv_list = adv_resp.json()
    assert len(adv_list) >= 7
    assert all(a["blocked"] is True for a in adv_list)
