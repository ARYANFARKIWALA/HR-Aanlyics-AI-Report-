"""Comprehensive Unit and Integration Tests for Phase 9 — HR Analytics Engine."""

import pytest
import pandas as pd
from analytics.reusable_services import HRAnalyticsEngine


@pytest.fixture
def sample_hr_dataset():
    """Generates synthetic HR reporting dataset with canonical attributes."""
    data = [
        {"department": "Engineering", "month": "2026-01", "attrition_count": 5, "headcount": 120, "salary": 110000.0, "status": "Terminated", "hire_date": "2023-01-15", "termination_date": "2026-01-20"},
        {"department": "Engineering", "month": "2026-02", "attrition_count": 3, "headcount": 122, "salary": 112000.0, "status": "Active", "hire_date": "2022-06-01", "termination_date": None},
        {"department": "Sales", "month": "2026-01", "attrition_count": 8, "headcount": 95, "salary": 95000.0, "status": "Terminated", "hire_date": "2024-03-10", "termination_date": "2026-01-15"},
        {"department": "Sales", "month": "2026-02", "attrition_count": 6, "headcount": 92, "salary": 96000.0, "status": "Active", "hire_date": "2021-11-20", "termination_date": None},
        {"department": "Human Resources", "month": "2026-01", "attrition_count": 1, "headcount": 30, "salary": 85000.0, "status": "Active", "hire_date": "2020-04-12", "termination_date": None},
        {"department": "Human Resources", "month": "2026-02", "attrition_count": 2, "headcount": 29, "salary": 86000.0, "status": "Terminated", "hire_date": "2023-08-18", "termination_date": "2026-02-10"},
    ]
    return pd.DataFrame(data)


def test_calculate_totals_and_averages(sample_hr_dataset):
    """Test totals and averages analytics services."""
    tot = HRAnalyticsEngine.calculate_totals(sample_hr_dataset, "attrition_count")
    assert tot["value"] == 25.0
    assert "Sum of numeric column" in tot["transformation"]

    avg = HRAnalyticsEngine.calculate_averages(sample_hr_dataset, "salary")
    assert avg["value"] == 97333.33
    assert "Mean calculation" in avg["transformation"]


def test_calculate_percentages_and_ratios(sample_hr_dataset):
    """Test percentage composition and metric ratios."""
    pct_df = HRAnalyticsEngine.calculate_percentages(sample_hr_dataset, "department", "attrition_count")
    assert "percentage" in pct_df.columns
    assert round(pct_df["percentage"].sum(), 1) == 100.0

    ratio_df = HRAnalyticsEngine.calculate_ratios(sample_hr_dataset, "attrition_count", "headcount", "attrition_ratio")
    assert "attrition_ratio" in ratio_df.columns
    assert (ratio_df["attrition_ratio"] >= 0).all()


def test_calculate_trends_and_growth_rate(sample_hr_dataset):
    """Test period-over-period trend analysis and growth rates."""
    eng_df = sample_hr_dataset[sample_hr_dataset["department"] == "Engineering"]
    trends = HRAnalyticsEngine.calculate_trends(eng_df, "month", "attrition_count")
    assert len(trends) == 2
    assert trends[1]["change_absolute"] == -2.0
    assert trends[1]["direction"] == "DECREASING"

    growth_df = HRAnalyticsEngine.calculate_growth_rate(eng_df, "month", "attrition_count")
    assert "growth_rate_pct" in growth_df.columns


def test_calculate_ranking_and_groups(sample_hr_dataset):
    """Test ordinal ranking and multi-dimensional grouping."""
    ranked = HRAnalyticsEngine.calculate_ranking(sample_hr_dataset, "attrition_count", ascending=False)
    assert "rank" in ranked.columns
    assert ranked.iloc[0]["attrition_count"] == 8

    grouped = HRAnalyticsEngine.calculate_group_analysis(
        sample_hr_dataset,
        group_cols=["department"],
        agg_dict={"attrition_count": "sum", "salary": "mean"}
    )
    assert len(grouped) == 3
    assert "Engineering" in grouped["department"].values


def test_calculate_attrition_turnover_tenure(sample_hr_dataset):
    """Test HR-specific KPI services: attrition rate, turnover, tenure."""
    att = HRAnalyticsEngine.calculate_attrition_rate(sample_hr_dataset)
    assert att["terminated_count"] == 3
    assert att["total_headcount"] == 6
    assert att["attrition_rate_pct"] == 50.0
    assert att["retention_rate_pct"] == 50.0

    ten = HRAnalyticsEngine.calculate_tenure(sample_hr_dataset, "hire_date", "termination_date")
    assert ten["avg_tenure_years"] > 0
    assert ten["median_tenure_years"] > 0
    assert "Computed delta" in ten["transformation"]


def test_automatic_visualization_recommendations(sample_hr_dataset):
    """Test automatic chart recommendations matching prompt specifications."""
    recs = HRAnalyticsEngine.recommend_visualizations(sample_hr_dataset)
    chart_types = [r["chart_type"] for r in recs]

    # Time series -> Line chart
    assert "line" in chart_types

    # Department comparison -> Bar chart
    assert "bar" in chart_types

    # Distribution -> Histogram
    assert "histogram" in chart_types

    # Composition -> Pie / Donut
    assert "pie" in chart_types

    # KPI -> Metric card
    assert "metric_card" in chart_types
