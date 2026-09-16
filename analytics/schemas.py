"""Pydantic schemas for Module 9 - HR Analytics Engine."""

from typing import Any

from pydantic import BaseModel


class ColumnClassification(BaseModel):
    column_name: str
    semantic_type: str  # CATEGORICAL, NUMERIC, CURRENCY, DATE, IDENTIFIER, BOOLEAN
    is_dimension: bool = False
    is_metric: bool = False


class ColumnProfile(BaseModel):
    column_name: str
    semantic_type: str
    dtype: str
    null_count: int
    null_pct: float
    unique_count: int
    min_val: Any | None = None
    max_val: Any | None = None
    mean_val: float | None = None
    median_val: float | None = None
    std_val: float | None = None


class KPISummary(BaseModel):
    total_records: int
    active_headcount: int | None = None
    terminated_headcount: int | None = None
    attrition_rate_pct: float | None = None
    retention_rate_pct: float | None = None
    avg_compensation: float | None = None
    median_compensation: float | None = None
    total_payroll: float | None = None
    avg_tenure_years: float | None = None
    gender_distribution: dict[str, float] = {}
    custom_kpis: dict[str, Any] = {}


class OutlierItem(BaseModel):
    column_name: str
    row_index: int
    identifier: str | None = None
    value: float
    method: str  # IQR, Z_SCORE
    lower_bound: float
    upper_bound: float
    severity: str = "MODERATE"  # MILD, MODERATE, EXTREME


class TrendItem(BaseModel):
    time_period: str
    metric_name: str
    value: float
    previous_value: float | None = None
    change_absolute: float | None = None
    change_pct: float | None = None
    direction: str = "STABLE"  # INCREASING, DECREASING, STABLE


class CorrelationItem(BaseModel):
    column_a: str
    column_b: str
    correlation_coefficient: float
    strength: str  # STRONG, MODERATE, WEAK
    interpretation: str


class SegmentationBreakdown(BaseModel):
    dimension: str
    segments: dict[str, dict[str, Any]] = {}


class DataQualityReport(BaseModel):
    quality_score: float  # 0 to 100
    total_rows: int
    completeness_pct: float
    anomaly_count: int
    issues: list[str] = []


class InsightItem(BaseModel):
    title: str
    category: str  # ATTRITION, COMPENSATION, DIVERSITY, PERFORMANCE, DATA_QUALITY
    insight_type: str  # ALERT, TREND, BENCHMARK, RECOMMENDATION
    text: str
    metric_citations: dict[str, Any] = {}


class RecommendedChart(BaseModel):
    chart_type: str  # bar, line, scatter, box, pie, heatmap
    title: str
    x_axis: str | None = None
    y_axis: str | None = None
    color_by: str | None = None
    description: str = ""


class AnalyticsRequest(BaseModel):
    execution_id: str | None = None
    dataset: list[dict[str, Any]] | None = None
    target_dimension: str | None = None
    target_metric: str | None = None


class AnalyticsResponse(BaseModel):
    analysis_id: str
    execution_id: str | None = None
    dataset_shape: str
    columns: list[str] = []
    classifications: list[ColumnClassification] = []
    profiles: list[ColumnProfile] = []
    kpis: KPISummary
    outliers: list[OutlierItem] = []
    trends: list[TrendItem] = []
    correlations: list[CorrelationItem] = []
    segmentations: list[SegmentationBreakdown] = []
    data_quality: DataQualityReport
    insights: list[InsightItem] = []
    recommended_charts: list[RecommendedChart] = []
