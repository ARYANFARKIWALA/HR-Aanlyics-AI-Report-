"""Module 10: Report Builder & Visualization."""

from .chart_builder import ChartBuilder
from .filter_manager import FilterManager
from .kpi_builder import KPIBuilder
from .schemas import (
    BuiltKPICard,
    BuiltReport,
    ChartConfig,
    FilterConfig,
    InsightCalloutConfig,
    KPICardConfig,
    ReportDefinition,
    TableColumnConfig,
    TableConfig,
)
from .service import ReportBuilderService
from .table_builder import TableBuilder
from .template_manager import TEMPLATES, TemplateManager

__all__ = [
    "TEMPLATES",
    "BuiltKPICard",
    "BuiltReport",
    "ChartBuilder",
    "ChartConfig",
    "FilterConfig",
    "FilterManager",
    "InsightCalloutConfig",
    "KPIBuilder",
    "KPICardConfig",
    "ReportBuilderService",
    "ReportDefinition",
    "TableBuilder",
    "TableColumnConfig",
    "TableConfig",
    "TemplateManager",
]
