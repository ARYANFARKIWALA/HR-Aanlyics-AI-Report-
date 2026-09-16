"""Pydantic schemas and layout models for Module 10 - Report Builder & Visualization."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class KPICardConfig(BaseModel):
    card_id: str
    title: str
    metric_field: str
    aggregation: str = "count"  # count, sum, avg, median, min, max, percentage
    format_type: str = "integer"  # integer, currency, percentage, decimal
    prefix: str = ""
    suffix: str = ""
    target_value: Optional[float] = None
    delta_text: Optional[str] = None
    delta_color: str = "normal"  # normal, inverse, off
    help_text: Optional[str] = None


class ChartConfig(BaseModel):
    chart_id: str
    chart_type: str  # bar, line, scatter, pie, donut, box, heatmap
    title: str
    x_axis: str
    y_axis: Optional[str] = None
    color_by: Optional[str] = None
    orientation: str = "v"  # v (vertical), h (horizontal)
    barmode: str = "group"  # group, stack
    show_legend: bool = True
    height: int = 400
    description: Optional[str] = None


class TableColumnConfig(BaseModel):
    field: str
    header: str
    format_type: str = "string"  # string, currency, percentage, date, badge
    width: Optional[int] = None
    sortable: bool = True


class TableConfig(BaseModel):
    table_id: str
    title: str
    columns: List[TableColumnConfig]
    page_size: int = 25
    enable_search: bool = True
    highlight_rules: Optional[Dict[str, Any]] = None  # e.g. {"field": "attrition_pct", "operator": ">", "threshold": 15.0, "color": "red"}


class FilterConfig(BaseModel):
    field: str
    label: str
    filter_type: str = "multiselect"  # multiselect, select, date_range, numeric_range
    default_value: Optional[Any] = None
    options: List[str] = []


class InsightCalloutConfig(BaseModel):
    callout_id: str
    title: str
    category: str
    text: str
    severity: str = "info"  # info, warning, success, alert


class ReportDefinition(BaseModel):
    report_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    category: str = "General HR"
    template_name: Optional[str] = None
    database_id: str = "sqlite_hr_default"
    kpi_cards: List[KPICardConfig] = []
    charts: List[ChartConfig] = []
    tables: List[TableConfig] = []
    filters: List[FilterConfig] = []
    callouts: List[InsightCalloutConfig] = []


class BuiltKPICard(BaseModel):
    card_id: str
    title: str
    value: str
    raw_value: float
    delta_text: Optional[str] = None
    delta_color: str = "normal"
    help_text: Optional[str] = None


class BuiltReport(BaseModel):
    report_id: str
    title: str
    description: Optional[str] = None
    category: str
    kpi_cards: List[BuiltKPICard] = []
    charts: List[Dict[str, Any]] = []  # Plotly figure dictionaries
    tables: List[Dict[str, Any]] = []
    available_filters: List[FilterConfig] = []
    callouts: List[InsightCalloutConfig] = []
    row_count: int = 0
    built_at: str
