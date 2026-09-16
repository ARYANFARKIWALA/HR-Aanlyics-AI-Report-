"""Analytics and visualizations package (Module 9)."""

from .metrics import HRMetricsCalculator
from .visualization import HRVisualizer
from .schemas import (
    AnalyticsRequest,
    AnalyticsResponse,
    KPISummary,
    ColumnClassification,
    ColumnProfile,
    OutlierItem,
    TrendItem,
    CorrelationItem,
    SegmentationBreakdown,
    DataQualityReport,
    InsightItem,
    RecommendedChart,
)
from .service import HRAnalyticsService

__all__ = [
    "HRMetricsCalculator",
    "HRVisualizer",
    "HRAnalyticsService",
    "AnalyticsRequest",
    "AnalyticsResponse",
    "KPISummary",
    "ColumnClassification",
    "ColumnProfile",
    "OutlierItem",
    "TrendItem",
    "CorrelationItem",
    "SegmentationBreakdown",
    "DataQualityReport",
    "InsightItem",
    "RecommendedChart",
]
