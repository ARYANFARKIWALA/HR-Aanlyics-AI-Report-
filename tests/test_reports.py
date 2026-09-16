"""Unit tests for Report Builder, PDF export, and Excel export."""

import pytest
from backend.database.connection import SessionLocal
from backend.database.models import User
from backend.services.report_service import ReportService


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_pdf_and_excel_export(db_session):
    admin_user = db_session.query(User).filter_by(username="admin").first()

    cols = ["department", "active_headcount", "avg_salary"]
    rows = [
        {"department": "Engineering", "active_headcount": 25, "avg_salary": 145000.0},
        {"department": "Sales", "active_headcount": 18, "avg_salary": 115000.0},
    ]

    report = ReportService.generate_report_payload(
        session=db_session,
        title="Department Compensation Snapshot",
        category="Compensation",
        sql_query="SELECT department, active_headcount, avg_salary FROM sample;",
        data_columns=cols,
        data_rows=rows,
        user=admin_user
    )

    assert report.report_id.startswith("REP-")
    assert report.kpis["active_headcount"] > 0
    assert len(report.data_rows) == 2

    # 1. Test PDF Export
    pdf_bytes = ReportService.export_pdf(report)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

    # 2. Test Excel Export
    excel_bytes = ReportService.export_excel(report)
    assert len(excel_bytes) > 1000
    assert excel_bytes.startswith(b"PK")  # ZIP/XLSX header
