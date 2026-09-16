"""Unit and Integration Tests for Module 9 — HR Analytics Engine."""

import pytest
import pandas as pd
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import SessionLocal, init_db
from analytics.schemas import AnalyticsRequest
from analytics.service import HRAnalyticsService
from analytics.column_classifier import ColumnClassifier
from analytics.profiler import DataProfiler
from analytics.kpi_engine import KPIEngine
from analytics.outlier_detection import OutlierDetector
from analytics.trend_analysis import TrendAnalyzer
from analytics.correlation import CorrelationAnalyzer
from analytics.segmentation import SegmentationEngine
from analytics.data_quality import DataQualityAuditor
from analytics.visualization_recommender import VisualizationRecommender
from analytics.insight_engine import InsightEngine


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


@pytest.fixture
def sample_hr_dataset():
    """Returns a realistic synthetic HR dataset."""
    return pd.DataFrame([
        {"id": 1, "name": "Alice", "department": "ENG", "status": "Active", "salary": 120000, "hire_date": "2020-01-15", "gender": "Female", "compa_ratio": 1.05},
        {"id": 2, "name": "Bob", "department": "ENG", "status": "Active", "salary": 115000, "hire_date": "2021-03-10", "gender": "Male", "compa_ratio": 1.00},
        {"id": 3, "name": "Charlie", "department": "SLS", "status": "Active", "salary": 95000, "hire_date": "2021-06-20", "gender": "Male", "compa_ratio": 0.95},
        {"id": 4, "name": "Diana", "department": "SLS", "status": "Terminated", "salary": 90000, "hire_date": "2022-01-05", "gender": "Female", "compa_ratio": 0.90},
        {"id": 5, "name": "Evan", "department": "HR", "status": "Active", "salary": 80000, "hire_date": "2022-04-12", "gender": "Male", "compa_ratio": 0.98},
        {"id": 6, "name": "Fiona", "department": "HR", "status": "Active", "salary": 85000, "hire_date": "2023-02-01", "gender": "Female", "compa_ratio": 1.02},
        # Outlier
        {"id": 7, "name": "George", "department": "ENG", "status": "Active", "salary": 380000, "hire_date": "2019-11-15", "gender": "Male", "compa_ratio": 1.60}
    ])


def test_column_classifier(sample_hr_dataset):
    """Verifies automatic classification of column semantic roles."""
    classes = ColumnClassifier.classify(sample_hr_dataset)
    cls_map = {c.column_name: c.semantic_type for c in classes}

    assert cls_map["id"] == "IDENTIFIER"
    assert cls_map["salary"] == "CURRENCY"
    assert cls_map["department"] == "CATEGORICAL"
    assert cls_map["hire_date"] == "DATE"
    assert cls_map["compa_ratio"] == "NUMERIC"


def test_deterministic_kpis(sample_hr_dataset):
    """Verifies exact deterministic calculation of Headcount, Turnover, and Salary."""
    kpis = KPIEngine.calculate_kpis(sample_hr_dataset)

    assert kpis.total_records == 7
    assert kpis.active_headcount == 6
    assert kpis.terminated_headcount == 1
    # Attrition = 1 / 7 = 14.29%
    assert kpis.attrition_rate_pct == 14.29
    assert kpis.retention_rate_pct == 85.71

    # Total payroll: 120k + 115k + 95k + 90k + 80k + 85k + 380k = 965,000
    assert kpis.total_payroll == 965000.0
    # Average salary: 965,000 / 7 = 137,857.14
    assert kpis.avg_compensation == 137857.14
    # Median salary of [80k, 85k, 90k, 95k, 115k, 120k, 380k] = 95,000
    assert kpis.median_compensation == 95000.0

    # Gender breakdown
    assert "Female" in kpis.gender_distribution
    assert "Male" in kpis.gender_distribution
    assert kpis.gender_distribution["Female"] == round((3 / 7) * 100, 1)


def test_iqr_outlier_detection(sample_hr_dataset):
    """Verifies detection of George's extreme 380k salary."""
    classes = ColumnClassifier.classify(sample_hr_dataset)
    outliers = OutlierDetector.detect_outliers(sample_hr_dataset, classes)

    assert len(outliers) >= 1
    salary_outliers = [o for o in outliers if o.column_name == "salary"]
    assert len(salary_outliers) == 1
    assert salary_outliers[0].value == 380000.0
    assert salary_outliers[0].method == "IQR"
    assert salary_outliers[0].severity in ["MODERATE", "EXTREME"]


def test_trend_analysis(sample_hr_dataset):
    """Verifies chronological trajectory grouping by year."""
    classes = ColumnClassifier.classify(sample_hr_dataset)
    trends = TrendAnalyzer.analyze_trends(sample_hr_dataset, classes)

    assert len(trends) >= 3
    # Check years 2019, 2020, 2021, 2022, 2023
    periods = [t.time_period for t in trends]
    assert "2019" in periods
    assert "2021" in periods


def test_correlation_analysis(sample_hr_dataset):
    """Verifies bivariate Pearson correlation between salary and compa_ratio."""
    classes = ColumnClassifier.classify(sample_hr_dataset)
    corrs = CorrelationAnalyzer.analyze_correlations(sample_hr_dataset, classes)

    assert len(corrs) >= 1
    pair = corrs[0]
    assert "salary" in [pair.column_a, pair.column_b]
    assert "compa_ratio" in [pair.column_a, pair.column_b]
    assert pair.correlation_coefficient > 0.5
    assert pair.strength in ["MODERATE", "STRONG"]


def test_segmentation_engine(sample_hr_dataset):
    """Verifies dimensional slicing across departments."""
    classes = ColumnClassifier.classify(sample_hr_dataset)
    segs = SegmentationEngine.segment(sample_hr_dataset, classes)

    assert len(segs) >= 1
    dept_seg = next((s for s in segs if s.dimension == "department"), None)
    assert dept_seg is not None
    assert "ENG" in dept_seg.segments
    assert dept_seg.segments["ENG"]["headcount"] == 3


def test_data_quality_auditor():
    """Verifies data quality scoring, duplicate identification, and chronological anomalies."""
    dirty_df = pd.DataFrame([
        {"id": 1, "name": "Valid", "salary": 100000, "hire_date": "2020-01-01", "termination_date": "2021-01-01"},
        {"id": 1, "name": "Duplicate ID", "salary": -5000, "hire_date": "2022-01-01", "termination_date": "2020-01-01"}  # Duplicate id, negative salary, term before hire!
    ])

    report = DataQualityAuditor.audit(dirty_df)
    assert report.quality_score < 90.0
    assert report.anomaly_count >= 3
    assert any("duplicate" in iss.lower() for iss in report.issues)
    assert any("negative" in iss.lower() for iss in report.issues)
    assert any("precedes" in iss.lower() for iss in report.issues)


def test_visualization_recommender(sample_hr_dataset):
    """Verifies appropriate chart type recommendations."""
    classes = ColumnClassifier.classify(sample_hr_dataset)
    recs = VisualizationRecommender.recommend(classes)

    types = [r.chart_type for r in recs]
    assert "bar" in types
    assert "line" in types
    assert "box" in types


def test_evidence_based_insights(sample_hr_dataset):
    """Verifies deterministic narrative insights with exact citations."""
    classes = ColumnClassifier.classify(sample_hr_dataset)
    kpis = KPIEngine.calculate_kpis(sample_hr_dataset)
    outliers = OutlierDetector.detect_outliers(sample_hr_dataset, classes)
    quality = DataQualityAuditor.audit(sample_hr_dataset)
    segs = SegmentationEngine.segment(sample_hr_dataset, classes)
    corrs = CorrelationAnalyzer.analyze_correlations(sample_hr_dataset, classes)

    insights = InsightEngine.generate_insights(
        kpis=kpis,
        outliers=outliers,
        quality=quality,
        segmentations=segs,
        correlations=corrs
    )

    assert len(insights) >= 3
    # Verify metric citations
    comp_insight = next((i for i in insights if i.category == "COMPENSATION"), None)
    assert comp_insight is not None
    assert comp_insight.metric_citations["avg_compensation"] == kpis.avg_compensation


def test_hr_analytics_service_full_pipeline(db_session, sample_hr_dataset):
    """Verifies end-to-end service execution on dataset."""
    service = HRAnalyticsService(db=db_session)
    req = AnalyticsRequest(dataset=sample_hr_dataset.to_dict(orient="records"))
    res = service.analyze(req)

    assert res.analysis_id.startswith("anl_")
    assert res.kpis.total_records == 7
    assert len(res.profiles) == len(sample_hr_dataset.columns)
    assert len(res.outliers) >= 1
    assert len(res.insights) >= 3
    assert len(res.recommended_charts) >= 3


def test_fastapi_analytics_endpoints(client, sample_hr_dataset):
    """Verifies FastAPI analytics endpoints."""
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Post dataset to /api/analytics/analyze
    resp = client.post(
        "/api/analytics/analyze",
        headers=headers,
        json={"dataset": sample_hr_dataset.to_dict(orient="records")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["kpis"]["total_records"] == 7
    assert len(data["insights"]) >= 3

    # 2. Historical audit endpoint
    audit_resp = client.get("/api/analytics/audit", headers=headers)
    assert audit_resp.status_code == 200
    assert len(audit_resp.json()["analytics_history"]) >= 1
