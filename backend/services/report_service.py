"""Report generation service coordinating report assembly, PDF, and Excel exports."""

from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from reports.builder import ReportBuilder, ReportData
from reports.export_excel import ExcelReportExporter
from reports.export_pdf import PDFReportExporter
from security.permissions import mask_pii_dataframe

from ..database.models import User


class ReportService:
    """Service handling multi-format enterprise report generation."""

    @classmethod
    def generate_report_payload(
        cls,
        session: Session,
        title: str,
        category: str,
        sql_query: str,
        data_columns: list[str],
        data_rows: list[dict[str, Any]],
        user: User,
        business_rules: str = "Standard payroll and effective-dating rules applied.",
        effective_dating_notes: str = "Current active point-in-time snapshot."
    ) -> ReportData:
        # Mask PII if needed
        df = pd.DataFrame(data_rows) if data_rows else pd.DataFrame(columns=data_columns)
        masked_df = mask_pii_dataframe(df, user.role)
        sanitized_rows = masked_df.to_dict(orient="records")

        return ReportBuilder.assemble_report(
            session=session,
            title=title,
            category=category,
            sql_query=sql_query,
            data_columns=data_columns,
            data_rows=sanitized_rows,
            requested_by=f"{user.full_name} ({user.role})",
            business_rules=business_rules,
            effective_dating_notes=effective_dating_notes
        )

    @classmethod
    def export_pdf(cls, report: ReportData) -> bytes:
        return PDFReportExporter.generate_pdf(report)

    @classmethod
    def export_excel(cls, report: ReportData) -> bytes:
        return ExcelReportExporter.generate_excel(report)
