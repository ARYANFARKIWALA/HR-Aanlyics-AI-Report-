"""Pydantic schemas and layout models for Module 10 - Report Builder & Visualization."""

from typing import Any

from pydantic import BaseModel


class KPICardConfig(BaseModel):
    card_id: str
    title: str
    metric_field: str
    aggregation: str = "count"  # count, sum, avg, median, min, max, percentage
    format_type: str = "integer"  # integer, currency, percentage, decimal
    prefix: str = ""
    suffix: str = ""
    target_value: float | None = None
    delta_text: str | None = None
    delta_color: str = "normal"  # normal, inverse, off
    help_text: str | None = None


class ChartConfig(BaseModel):
    chart_id: str
    chart_type: str  # bar, line, scatter, pie, donut, box, heatmap
    title: str
    x_axis: str
    y_axis: str | None = None
    color_by: str | None = None
    orientation: str = "v"  # v (vertical), h (horizontal)
    barmode: str = "group"  # group, stack
    show_legend: bool = True
    height: int = 400
    description: str | None = None


class TableColumnConfig(BaseModel):
    field: str
    header: str
    format_type: str = "string"  # string, currency, percentage, date, badge
    width: int | None = None
    sortable: bool = True


class TableConfig(BaseModel):
    table_id: str
    title: str
    columns: list[TableColumnConfig]
    page_size: int = 25
    enable_search: bool = True
    highlight_rules: dict[str, Any] | None = None  # e.g. {"field": "attrition_pct", "operator": ">", "threshold": 15.0, "color": "red"}


class FilterConfig(BaseModel):
    field: str
    label: str
    filter_type: str = "multiselect"  # multiselect, select, date_range, numeric_range
    default_value: Any | None = None
    options: list[str] = []


class InsightCalloutConfig(BaseModel):
    callout_id: str
    title: str
    category: str
    text: str
    severity: str = "info"  # info, warning, success, alert


class ReportDefinition(BaseModel):
    report_id: str | None = None
    title: str
    description: str | None = None
    category: str = "General HR"
    template_name: str | None = None
    database_id: str = "sqlite_hr_default"
    kpi_cards: list[KPICardConfig] = []
    charts: list[ChartConfig] = []
    tables: list[TableConfig] = []
    filters: list[FilterConfig] = []
    callouts: list[InsightCalloutConfig] = []


class BuiltKPICard(BaseModel):
    card_id: str
    title: str
    value: str
    raw_value: float
    delta_text: str | None = None
    delta_color: str = "normal"
    help_text: str | None = None


class BuiltReport(BaseModel):
    report_id: str
    title: str
    description: str | None = None
    category: str
    kpi_cards: list[BuiltKPICard] = []
    charts: list[dict[str, Any]] = []  # Plotly figure dictionaries
    tables: list[dict[str, Any]] = []
    available_filters: list[FilterConfig] = []
    callouts: list[InsightCalloutConfig] = []
    row_count: int = 0
    built_at: str
