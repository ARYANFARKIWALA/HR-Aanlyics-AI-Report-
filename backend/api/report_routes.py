"""Report generation and export API routes."""

from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user
from ..database.connection import get_db
from ..database.models import User
from ..services.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["Reports & Exports"])


class ReportGenerateRequest(BaseModel):
    title: str
    category: str
    sql_query: str
    data_columns: list[str]
    data_rows: list[dict[str, Any]]
    business_rules: str | None = "Standard enterprise payroll and effective-dating rules applied."
    effective_dating_notes: str | None = "Current active point-in-time snapshot."


@router.post("/generate")
def generate_report_payload(
    req: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assembles full report payload with KPIs, AI narrative, and tables."""
    report = ReportService.generate_report_payload(
        session=db,
        title=req.title,
        category=req.category,
        sql_query=req.sql_query,
        data_columns=req.data_columns,
        data_rows=req.data_rows,
        user=current_user,
        business_rules=req.business_rules,
        effective_dating_notes=req.effective_dating_notes
    )
    return report.to_dict()


@router.post("/export/pdf")
def export_pdf_report(
    req: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates and downloads styled enterprise PDF report."""
    report = ReportService.generate_report_payload(
        session=db,
        title=req.title,
        category=req.category,
        sql_query=req.sql_query,
        data_columns=req.data_columns,
        data_rows=req.data_rows,
        user=current_user,
        business_rules=req.business_rules,
        effective_dating_notes=req.effective_dating_notes
    )
    pdf_bytes = ReportService.export_pdf(report)
    filename = f"{report.report_id}_{report.title.replace(' ', '_')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/export/excel")
def export_excel_report(
    req: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates and downloads styled multi-tab Excel workbook."""
    report = ReportService.generate_report_payload(
        session=db,
        title=req.title,
        category=req.category,
        sql_query=req.sql_query,
        data_columns=req.data_columns,
        data_rows=req.data_rows,
        user=current_user,
        business_rules=req.business_rules,
        effective_dating_notes=req.effective_dating_notes
    )
    excel_bytes = ReportService.export_excel(report)
    filename = f"{report.report_id}_{report.title.replace(' ', '_')}.xlsx"

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
