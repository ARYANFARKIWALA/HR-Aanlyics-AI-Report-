"""Pre-configured enterprise HR report templates."""

from typing import Dict, List, Optional, Any
from .schemas import (
    ReportDefinition,
    KPICardConfig,
    ChartConfig,
    TableConfig,
    TableColumnConfig,
    FilterConfig,
    InsightCalloutConfig
)

TEMPLATES: Dict[str, ReportDefinition] = {
    "executive_overview": ReportDefinition(
        report_id="tpl_exec_overview",
        title="Executive HR Leadership Overview",
        description="Comprehensive C-suite briefing on organizational headcount, turnover, compensation, and diversity.",
        category="Executive",
        kpi_cards=[
            KPICardConfig(card_id="kpi_headcount", title="Active Headcount", metric_field="status", aggregation="count", format_type="integer"),
            KPICardConfig(card_id="kpi_salary", title="Average Salary", metric_field="base_salary", aggregation="avg", format_type="currency"),
            KPICardConfig(card_id="kpi_payroll", title="Annualized Payroll", metric_field="base_salary", aggregation="sum", format_type="currency"),
            KPICardConfig(card_id="kpi_compa", title="Compa-Ratio Average", metric_field="compa_ratio", aggregation="avg", format_type="decimal"),
        ],
        charts=[
            ChartConfig(chart_id="chart_dept_headcount", chart_type="bar", title="Headcount by Department", x_axis="department"),
            ChartConfig(chart_id="chart_salary_spread", chart_type="box", title="Salary Distribution Across Departments", x_axis="department", y_axis="base_salary"),
            ChartConfig(chart_id="chart_gender_donut", chart_type="donut", title="Gender Diversity Ratio", x_axis="gender")
        ],
        tables=[
            TableConfig(
                table_id="tbl_dept_summary",
                title="Departmental Summary",
                columns=[
                    TableColumnConfig(field="department", header="Department"),
                    TableColumnConfig(field="job_title", header="Title"),
                    TableColumnConfig(field="base_salary", header="Base Salary", format_type="currency"),
                    TableColumnConfig(field="status", header="Status")
                ]
            )
        ]
    ),
    "attrition_deep_dive": ReportDefinition(
        report_id="tpl_attrition_deep_dive",
        title="Attrition & Retention Deep Dive",
        description="Detailed turnover dynamics, voluntary vs involuntary exits, and departmental attrition vectors.",
        category="Attrition",
        kpi_cards=[
            KPICardConfig(card_id="kpi_total_exits", title="Total Terminations", metric_field="status", aggregation="count", format_type="integer"),
            KPICardConfig(card_id="kpi_tenure", title="Average Tenure", metric_field="tenure_years", aggregation="avg", format_type="decimal", suffix=" yrs"),
        ],
        charts=[
            ChartConfig(chart_id="chart_attrition_dept", chart_type="bar", title="Exits by Department", x_axis="department"),
            ChartConfig(chart_id="chart_attrition_type", chart_type="pie", title="Voluntary vs Involuntary Split", x_axis="attrition_type")
        ],
        tables=[
            TableConfig(
                table_id="tbl_exits",
                title="Historical Exits Log",
                columns=[
                    TableColumnConfig(field="employee_id", header="Employee ID"),
                    TableColumnConfig(field="department", header="Department"),
                    TableColumnConfig(field="hire_date", header="Hire Date"),
                    TableColumnConfig(field="status", header="Status")
                ]
            )
        ]
    ),
    "compensation_equity": ReportDefinition(
        report_id="tpl_comp_equity",
        title="Compensation Equity & Band Analysis",
        description="Salary band compliance, market compa-ratios, and outlier detection.",
        category="Compensation",
        kpi_cards=[
            KPICardConfig(card_id="kpi_avg_salary", title="Average Base Salary", metric_field="base_salary", aggregation="avg", format_type="currency"),
            KPICardConfig(card_id="kpi_median_salary", title="Median Base Salary", metric_field="base_salary", aggregation="median", format_type="currency"),
            KPICardConfig(card_id="kpi_total_budget", title="Payroll Expenditure", metric_field="base_salary", aggregation="sum", format_type="currency"),
        ],
        charts=[
            ChartConfig(chart_id="chart_comp_box", chart_type="box", title="Salary Bands by Job Family", x_axis="job_family", y_axis="base_salary"),
            ChartConfig(chart_id="chart_compa_scatter", chart_type="scatter", title="Base Salary vs Compa-Ratio", x_axis="base_salary", y_axis="compa_ratio")
        ],
        tables=[
            TableConfig(
                table_id="tbl_compensation",
                title="Compensation Records",
                columns=[
                    TableColumnConfig(field="employee_id", header="ID"),
                    TableColumnConfig(field="job_title", header="Job Title"),
                    TableColumnConfig(field="base_salary", header="Base Salary", format_type="currency"),
                    TableColumnConfig(field="compa_ratio", header="Compa-Ratio", format_type="decimal")
                ]
            )
        ]
    )
}


class TemplateManager:
    """Manages pre-built HR report templates."""

    @classmethod
    def list_templates(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": key,
                "title": tpl.title,
                "description": tpl.description,
                "category": tpl.category,
                "kpi_count": len(tpl.kpi_cards),
                "chart_count": len(tpl.charts),
                "table_count": len(tpl.tables)
            }
            for key, tpl in TEMPLATES.items()
        ]

    @classmethod
    def get_template(cls, key: str) -> Optional[ReportDefinition]:
        return TEMPLATES.get(key)
