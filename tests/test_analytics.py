"""Unit tests for HR Analytics and KPI calculations."""

import pytest

from analytics.metrics import HRMetricsCalculator
from backend.database.connection import SessionLocal


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_executive_kpis(db_session):
    kpis = HRMetricsCalculator.get_executive_summary_kpis(db_session)
    assert kpis["total_headcount"] > 0
    assert kpis["active_headcount"] > 0
    assert kpis["attrition_rate_pct"] >= 0.0
    assert kpis["avg_base_salary"] > 0.0
    assert kpis["avg_compa_ratio"] > 0.0
    assert kpis["female_representation_pct"] > 0.0
    assert len(kpis["department_breakdown"]) == 7


def test_department_attrition_breakdown(db_session):
    attrition = HRMetricsCalculator.get_attrition_by_department(db_session)
    assert len(attrition) > 0
    for dept in attrition:
        assert "department" in dept
        assert "turnover_pct" in dept
        assert dept["turnover_pct"] >= 0.0
