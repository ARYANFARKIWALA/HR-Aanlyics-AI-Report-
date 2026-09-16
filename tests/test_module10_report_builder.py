"""Unit and Integration Tests for Module 10 — Report Builder & Visualization."""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from report_builder.chart_builder import ChartBuilder
from report_builder.filter_manager import FilterManager
from report_builder.kpi_builder import KPIBuilder
from report_builder.schemas import (
    ChartConfig,
    KPICardConfig,
    TableColumnConfig,
    TableConfig,
)
from report_builder.service import ReportBuilderService
from report_builder.table_builder import TableBuilder
from report_builder.template_manager import TemplateManager


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture
def sample_report_data():
    return pd.DataFrame([
        {"department": "ENG", "job_title": "Engineer", "base_salary": 140000, "status": "Active", "gender": "Female", "compa_ratio": 1.1},
        {"department": "ENG", "job_title": "Senior Engineer", "base_salary": 160000, "status": "Active", "gender": "Male", "compa_ratio": 1.2},
        {"department": "SLS", "job_title": "Account Exec", "base_salary": 95000, "status": "Active", "gender": "Male", "compa_ratio": 0.95},
        {"department": "SLS", "job_title": "Sales Rep", "base_salary": 80000, "status": "Terminated", "gender": "Female", "compa_ratio": 0.90},
        {"department": "HR", "job_title": "HR Generalist", "base_salary": 85000, "status": "Active", "gender": "Female", "compa_ratio": 1.0}
    ])


def test_chart_builder_types(sample_report_data):
    """Verifies that Plotly charts for bar, line, pie, box, and scatter are constructed validly."""
    # 1. Bar chart
    bar_conf = ChartConfig(chart_id="b1", chart_type="bar", title="Salary by Dept", x_axis="department", y_axis="base_salary")
    bar_fig = ChartBuilder.build_chart(sample_report_data, bar_conf)
    assert "data" in bar_fig
    assert len(bar_fig["data"]) > 0

    # 2. Donut / Pie chart
    pie_conf = ChartConfig(chart_id="p1", chart_type="donut", title="Gender Diversity", x_axis="gender")
    pie_fig = ChartBuilder.build_chart(sample_report_data, pie_conf)
    assert "data" in pie_fig
    assert pie_fig["data"][0]["type"] == "pie"

    # 3. Box plot
    box_conf = ChartConfig(chart_id="bx1", chart_type="box", title="Salary Spread", x_axis="department", y_axis="base_salary")
    box_fig = ChartBuilder.build_chart(sample_report_data, box_conf)
    assert "data" in box_fig
    assert box_fig["data"][0]["type"] == "box"

    # 4. Scatter plot
    scatter_conf = ChartConfig(chart_id="s1", chart_type="scatter", title="Salary vs Compa", x_axis="base_salary", y_axis="compa_ratio")
    scatter_fig = ChartBuilder.build_chart(sample_report_data, scatter_conf)
    assert "data" in scatter_fig
    assert scatter_fig["data"][0]["type"] == "scatter"


def test_kpi_builder_formatting(sample_report_data):
    """Verifies calculation and formatting of Currency, Integer, and Decimal KPIs."""
    # Average Salary -> Currency
    kpi_sal = KPICardConfig(card_id="k1", title="Avg Salary", metric_field="base_salary", aggregation="avg", format_type="currency")
    built_sal = KPIBuilder.build_kpi(sample_report_data, kpi_sal)
    assert built_sal.value.startswith("$")
    assert built_sal.raw_value == 112000.0

    # Total Headcount -> Integer
    kpi_cnt = KPICardConfig(card_id="k2", title="Headcount", metric_field="*", aggregation="count", format_type="integer")
    built_cnt = KPIBuilder.build_kpi(sample_report_data, kpi_cnt)
    assert built_cnt.value == "5"
    assert built_cnt.raw_value == 5.0

    # Compa-Ratio -> Decimal
    kpi_cr = KPICardConfig(card_id="k3", title="Compa-Ratio", metric_field="compa_ratio", aggregation="median", format_type="decimal")
    built_cr = KPIBuilder.build_kpi(sample_report_data, kpi_cr)
    assert built_cr.value == "1.00"


def test_table_builder_columns(sample_report_data):
    """Verifies column filtering and currency formatting in tabular builder."""
    tbl_conf = TableConfig(
        table_id="t1",
        title="Department Table",
        columns=[
            TableColumnConfig(field="department", header="Dept"),
            TableColumnConfig(field="base_salary", header="Salary", format_type="currency")
        ],
        page_size=3
    )
    res = TableBuilder.build_table(sample_report_data, tbl_conf)
    assert res["table_id"] == "t1"
    assert len(res["rows"]) == 3
    assert res["total_rows"] == 5
    assert res["rows"][0]["base_salary"].startswith("$")


def test_filter_manager(sample_report_data):
    """Verifies dataset filtering and auto-discovery of filter controls."""
    # 1. Apply multiselect filter on department
    filtered = FilterManager.apply_filters(sample_report_data, {"department": ["ENG"]})
    assert len(filtered) == 2
    assert set(filtered["department"]) == {"ENG"}

    # 2. Filter discovery
    filters = FilterManager.discover_filters(sample_report_data)
    fields = [f.field for f in filters]
    assert "department" in fields
    assert "status" in fields


def test_template_manager_and_service_assembly(sample_report_data):
    """Verifies template retrieval and end-to-end report building."""
    templates = TemplateManager.list_templates()
    assert len(templates) >= 3

    # Build report from template
    built = ReportBuilderService.build_from_template("executive_overview", sample_report_data)
    assert built.title == "Executive HR Leadership Overview"
    assert len(built.kpi_cards) == 4
    assert len(built.charts) == 3
    assert len(built.tables) == 1
    assert built.row_count == 5


def test_fastapi_report_builder_endpoints(client, sample_report_data):
    """Verifies FastAPI endpoints for listing templates and building reports."""
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List templates
    tpl_resp = client.get("/api/report-builder/templates", headers=headers)
    assert tpl_resp.status_code == 200
    assert len(tpl_resp.json()["templates"]) >= 3

    # 2. Build report via API
    build_resp = client.post(
        "/api/report-builder/build",
        headers=headers,
        json={
            "template_key": "executive_overview",
            "dataset": sample_report_data.to_dict(orient="records")
        }
    )
    assert build_resp.status_code == 200
    report_data = build_resp.json()
    assert report_data["title"] == "Executive HR Leadership Overview"
    assert len(report_data["kpi_cards"]) == 4
    assert len(report_data["charts"]) == 3
