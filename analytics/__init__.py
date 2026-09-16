"""Analytics and visualizations package (Module 9)."""

from .metrics import HRMetricsCalculator
from .schemas import (
    AnalyticsRequest,
    AnalyticsResponse,
    ColumnClassification,
    ColumnProfile,
    CorrelationItem,
    DataQualityReport,
    InsightItem,
    KPISummary,
    OutlierItem,
    RecommendedChart,
    SegmentationBreakdown,
    TrendItem,
)
from .service import HRAnalyticsService
from .visualization import HRVisualizer

__all__ = [
    "AnalyticsRequest",
    "AnalyticsResponse",
    "ColumnClassification",
    "ColumnProfile",
    "CorrelationItem",
    "DataQualityReport",
    "HRAnalyticsService",
    "HRMetricsCalculator",
    "HRVisualizer",
    "InsightItem",
    "KPISummary",
    "OutlierItem",
    "RecommendedChart",
    "SegmentationBreakdown",
    "TrendItem",
]
