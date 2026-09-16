"""Central Report Builder & Visualization Service (Module 10)."""

import datetime
import uuid
from typing import Any

import pandas as pd

from .chart_builder import ChartBuilder
from .filter_manager import FilterManager
from .kpi_builder import KPIBuilder
from .schemas import BuiltKPICard, BuiltReport, ReportDefinition
from .table_builder import TableBuilder
from .template_manager import TemplateManager


class ReportBuilderService:
    """Renders customized and template-driven executive HR reports."""

    @classmethod
    def build_report(
        cls,
        definition: ReportDefinition,
        df: pd.DataFrame,
        active_filters: dict[str, Any] | None = None
    ) -> BuiltReport:
        report_id = definition.report_id or f"rep_{uuid.uuid4().hex}"
        now = datetime.datetime.now(datetime.UTC).isoformat()

        # 1. Apply global dynamic filters
        filtered_df = FilterManager.apply_filters(df, active_filters or {})

        # 2. Build KPI Cards
        built_kpis: list[BuiltKPICard] = []
        for k_conf in definition.kpi_cards:
            built_kpis.append(KPIBuilder.build_kpi(filtered_df, k_conf))

        # 3. Build Plotly Charts
        built_charts: list[dict[str, Any]] = []
        for c_conf in definition.charts:
            built_charts.append(ChartBuilder.build_chart(filtered_df, c_conf))

        # 4. Build Tables
        built_tables: list[dict[str, Any]] = []
        for t_conf in definition.tables:
            built_tables.append(TableBuilder.build_table(filtered_df, t_conf))

        # 5. Determine available filters
        available_filters = definition.filters
        if not available_filters:
            available_filters = FilterManager.discover_filters(df)

        return BuiltReport(
            report_id=report_id,
            title=definition.title,
            description=definition.description,
            category=definition.category,
            kpi_cards=built_kpis,
            charts=built_charts,
            tables=built_tables,
            available_filters=available_filters,
            callouts=definition.callouts,
            row_count=len(filtered_df),
            built_at=now
        )

    @classmethod
    def build_from_template(
        cls,
        template_key: str,
        df: pd.DataFrame,
        active_filters: dict[str, Any] | None = None
    ) -> BuiltReport:
        tpl = TemplateManager.get_template(template_key)
        if not tpl:
            raise ValueError(f"Report template '{template_key}' not found.")
        return cls.build_report(definition=tpl, df=df, active_filters=active_filters)
