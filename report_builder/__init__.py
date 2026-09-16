"""Module 10: Report Builder & Visualization."""

from .schemas import (
    KPICardConfig,
    ChartConfig,
    TableConfig,
    TableColumnConfig,
    FilterConfig,
    InsightCalloutConfig,
    ReportDefinition,
    BuiltKPICard,
    BuiltReport,
)
from .service import ReportBuilderService
from .template_manager import TemplateManager, TEMPLATES
from .chart_builder import ChartBuilder
from .kpi_builder import KPIBuilder
from .table_builder import TableBuilder
from .filter_manager import FilterManager

__all__ = [
    "KPICardConfig",
    "ChartConfig",
    "TableConfig",
    "TableColumnConfig",
    "FilterConfig",
    "InsightCalloutConfig",
    "ReportDefinition",
    "BuiltKPICard",
    "BuiltReport",
    "ReportBuilderService",
    "TemplateManager",
    "TEMPLATES",
    "ChartBuilder",
    "KPIBuilder",
    "TableBuilder",
    "FilterManager",
]
