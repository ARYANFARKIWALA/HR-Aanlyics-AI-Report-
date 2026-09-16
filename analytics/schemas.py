"""Pydantic schemas for Module 9 - HR Analytics Engine."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


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
    min_val: Optional[Any] = None
    max_val: Optional[Any] = None
    mean_val: Optional[float] = None
    median_val: Optional[float] = None
    std_val: Optional[float] = None


class KPISummary(BaseModel):
    total_records: int
    active_headcount: Optional[int] = None
    terminated_headcount: Optional[int] = None
    attrition_rate_pct: Optional[float] = None
    retention_rate_pct: Optional[float] = None
    avg_compensation: Optional[float] = None
    median_compensation: Optional[float] = None
    total_payroll: Optional[float] = None
    avg_tenure_years: Optional[float] = None
    gender_distribution: Dict[str, float] = {}
    custom_kpis: Dict[str, Any] = {}


class OutlierItem(BaseModel):
    column_name: str
    row_index: int
    identifier: Optional[str] = None
    value: float
    method: str  # IQR, Z_SCORE
    lower_bound: float
    upper_bound: float
    severity: str = "MODERATE"  # MILD, MODERATE, EXTREME


class TrendItem(BaseModel):
    time_period: str
    metric_name: str
    value: float
    previous_value: Optional[float] = None
    change_absolute: Optional[float] = None
    change_pct: Optional[float] = None
    direction: str = "STABLE"  # INCREASING, DECREASING, STABLE


class CorrelationItem(BaseModel):
    column_a: str
    column_b: str
    correlation_coefficient: float
    strength: str  # STRONG, MODERATE, WEAK
    interpretation: str


class SegmentationBreakdown(BaseModel):
    dimension: str
    segments: Dict[str, Dict[str, Any]] = {}


class DataQualityReport(BaseModel):
    quality_score: float  # 0 to 100
    total_rows: int
    completeness_pct: float
    anomaly_count: int
    issues: List[str] = []


class InsightItem(BaseModel):
    title: str
    category: str  # ATTRITION, COMPENSATION, DIVERSITY, PERFORMANCE, DATA_QUALITY
    insight_type: str  # ALERT, TREND, BENCHMARK, RECOMMENDATION
    text: str
    metric_citations: Dict[str, Any] = {}


class RecommendedChart(BaseModel):
    chart_type: str  # bar, line, scatter, box, pie, heatmap
    title: str
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    color_by: Optional[str] = None
    description: str = ""


class AnalyticsRequest(BaseModel):
    execution_id: Optional[str] = None
    dataset: Optional[List[Dict[str, Any]]] = None
    target_dimension: Optional[str] = None
    target_metric: Optional[str] = None


class AnalyticsResponse(BaseModel):
    analysis_id: str
    execution_id: Optional[str] = None
    dataset_shape: str
    columns: List[str] = []
    classifications: List[ColumnClassification] = []
    profiles: List[ColumnProfile] = []
    kpis: KPISummary
    outliers: List[OutlierItem] = []
    trends: List[TrendItem] = []
    correlations: List[CorrelationItem] = []
    segmentations: List[SegmentationBreakdown] = []
    data_quality: DataQualityReport
    insights: List[InsightItem] = []
    recommended_charts: List[RecommendedChart] = []
