"""Comprehensive Unit and Integration Tests for Phase 10 — HR Report Builder."""

import pytest
from backend.database.connection import SessionLocal, init_db
from backend.database.models import User
from report_builder.pipeline_service import EndToEndReportBuilderService


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_end_to_end_report_builder_pipeline(db_session):
    """
    Test full 7-stage pipeline:
    Question -> SQL -> Validated SQL -> Results -> Analytics -> Visualization -> Report.
    """
    admin_user = db_session.query(User).filter(User.username == "admin").first()
    service = EndToEndReportBuilderService(db=db_session)

    canonical_question = "Show monthly employee attrition by department for 2026."
    res = service.generate_report_from_question(
        question=canonical_question,
        database_id="sqlite_hr_default",
        user=admin_user,
        save_report=True
    )

    assert res["status"] == "SUCCESS"

    # Verify all 7 preserved attributes
    assert res["question"] == canonical_question
    assert "employees" in res["sql_query"]
    assert "departments" in res["sql_query"]
    assert res["database_id"] == "sqlite_hr_default"
    assert "knowledge_sources" in res
    assert "timestamp" in res
    assert res["user"] == "admin"
    assert res["report_version"] >= 1

    # Verify pipeline outputs
    assert len(res["columns"]) > 0
    assert len(res["recommended_visualizations"]) > 0
    assert "kpis" in res
    assert res["report_data"] is not None


def test_report_exports_csv_excel_pdf(db_session):
    """Test exporting generated report to CSV, Excel, and PDF formats."""
    admin_user = db_session.query(User).filter(User.username == "admin").first()
    service = EndToEndReportBuilderService(db=db_session)

    res = service.generate_report_from_question(
        question="Show active headcount by department",
        database_id="sqlite_hr_default",
        user=admin_user,
        save_report=False
    )
    report_data = res["report_data"]

    # 1. Export CSV
    csv_out = service.export_csv(report_data)
    assert isinstance(csv_out, str)
    assert len(csv_out) > 0
    assert "department" in csv_out.lower() or "name" in csv_out.lower() or "id" in csv_out.lower()

    # 2. Export Excel
    excel_bytes = service.export_excel(report_data)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 500  # Excel zip container

    # 3. Export PDF
    pdf_bytes = service.export_pdf(report_data)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500  # PDF binary container
    assert pdf_bytes.startswith(b"%PDF")
