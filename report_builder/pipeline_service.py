"""End-to-End HR Report Builder Pipeline Service (Module 10).

Orchestrates the 7-stage automated report generation pipeline:
Natural language question
        ↓
Generated SQL (Module 6)
        ↓
Validated SQL (Module 7)
        ↓
Results (Module 8)
        ↓
Analytics (Module 9)
        ↓
Visualization (Charts, KPIs, Tables)
        ↓
Report (CSV, Excel, PDF + Saved Report with Versioning & Sharing)

Preserves:
- question
- SQL
- database
- knowledge sources
- timestamp
- user
- report version
"""

import csv
import datetime
import io
import uuid
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from analytics.reusable_services import HRAnalyticsEngine
from backend.database.models import User
from query_execution.schemas import ExecuteQueryRequest
from query_execution.service import QueryExecutionService
from reports.builder import ReportData
from reports.export_excel import ExcelReportExporter
from reports.export_pdf import PDFReportExporter
from reports_lifecycle.report_service import ReportLifecycleService
from reports_lifecycle.schemas import ReportCreateRequest
from sql_validator.schemas import SQLValidationRequest
from sql_validator.service import SQLValidatorService
from text_to_sql.schemas import TextToSQLRequest
from text_to_sql.service import TextToSQLService


class EndToEndReportBuilderService:
    """Coordinates seamless transformation from natural language to executive HR report."""

    def __init__(self, db: Session):
        self.db = db
        self.text_to_sql_service = TextToSQLService(db)
        self.sql_validator_service = SQLValidatorService(db)
        self.query_execution_service = QueryExecutionService(db)

    def generate_report_from_question(
        self,
        question: str,
        database_id: str = "sqlite_hr_default",
        user: User | None = None,
        title: str | None = None,
        description: str | None = None,
        save_report: bool = False,
        category: str = "Headcount & Workforce Planning"
    ) -> dict[str, Any]:
        """
        Executes the full 7-stage chain.
        Strict invariant: Never bypasses Module 7 validation.
        """
        now = datetime.datetime.now(datetime.UTC)
        author = user.username if user else "HR Analyst"
        user_role = user.role if user else "admin"

        # Stage 1 & 2: Natural Language -> Generated SQL
        t2s_req = TextToSQLRequest(
            query=question,
            database_id=database_id,
            user_role=user_role,
            include_explanation=True,
            include_plan=True
        )
        t2s_resp = self.text_to_sql_service.generate_sql(t2s_req)
        if t2s_resp.status != "SUCCESS" or not t2s_resp.sql:
            return {
                "status": "FAILED_GENERATION",
                "message": t2s_resp.message or "Failed to generate SQL from question.",
                "t2s_response": t2s_resp.model_dump()
            }

        generated_sql = t2s_resp.sql

        # Stage 3: Generated SQL -> Validated SQL
        val_req = SQLValidationRequest(
            sql=generated_sql,
            database_id=database_id,
            username=author,
            user_role=user_role
        )
        val_resp = self.sql_validator_service.validate_query(val_req)
        if val_resp.status != "APPROVED" or not val_resp.validation_id:
            return {
                "status": "REJECTED_BY_SECURITY",
                "message": val_resp.safe_error_explanation or "Query was rejected by SQL security validator.",
                "validation_response": val_resp.model_dump()
            }

        # Stage 4: Validated SQL -> Execution Results
        exec_req = ExecuteQueryRequest(
            validation_id=val_resp.validation_id,
            bypass_cache=True
        )
        exec_resp = self.query_execution_service.execute(exec_req, user=user)

        # Stage 5: Results -> Analytics
        df = pd.DataFrame(exec_resp.rows, columns=exec_resp.columns) if exec_resp.rows else pd.DataFrame(columns=exec_resp.columns)
        analytics_recs = HRAnalyticsEngine.recommend_visualizations(df)

        # Calculate high-level KPIs from dataset
        kpi_metrics = {}
        if not df.empty:
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    tot = HRAnalyticsEngine.calculate_totals(df, col)
                    avg = HRAnalyticsEngine.calculate_averages(df, col)
                    kpi_metrics[f"total_{col}"] = tot["value"]
                    kpi_metrics[f"avg_{col}"] = avg["value"]

        kpi_metrics["row_count"] = exec_resp.row_count
        kpi_metrics["execution_time_seconds"] = exec_resp.execution_time

        # Stage 6: Visualization Configuration
        report_title = title or f"HR Analytics Report: {question}"
        report_description = description or f"Automated report synthesized for prompt: '{question}'"

        # Knowledge sources
        knowledge_sources = {
            "applied_rules": t2s_resp.applied_rules,
            "reused_reports": t2s_resp.reused_reports,
            "dialect": t2s_resp.dialect,
            "confidence_score": t2s_resp.confidence_score
        }

        # Stage 7: Assemble Report Data
        report_data = ReportData(
            report_id=f"rep_{uuid.uuid4().hex[:10]}",
            title=report_title,
            category=category,
            requested_by=author,
            generated_at=now.strftime("%B %d, %Y - %H:%M UTC"),
            kpis=kpi_metrics,
            executive_summary=t2s_resp.explanation or f"Analysis based on: {question}",
            data_columns=exec_resp.columns,
            data_rows=exec_resp.rows,
            sql_query=generated_sql,
            business_rules=f"Validated via Module 7 Token {val_resp.validation_id}. Rules applied: {len(t2s_resp.applied_rules)}",
            effective_dating_notes="Strict read-only execution with effective-dating snapshot filters."
        )

        saved_report_id = None
        current_version = 1

        # Save report if requested
        if save_report:
            save_req = ReportCreateRequest(
                title=report_title,
                description=report_description,
                category=category,
                database_id=database_id,
                sql_query=generated_sql,
                layout_config={
                    "question": question,
                    "database_id": database_id,
                    "knowledge_sources": knowledge_sources,
                    "created_at": now.isoformat(),
                    "author": author,
                    "version": 1,
                    "recommended_charts": analytics_recs
                }
            )
            saved_report = ReportLifecycleService.create_report(
                db=self.db,
                req=save_req,
                user=user
            )
            saved_report_id = saved_report.report_id
            current_version = saved_report.current_version

        return {
            "status": "SUCCESS",
            "report_id": saved_report_id or report_data.report_id,
            "title": report_title,
            "description": report_description,
            "question": question,
            "database_id": database_id,
            "sql_query": generated_sql,
            "validation_id": val_resp.validation_id,
            "execution_id": exec_resp.execution_id,
            "knowledge_sources": knowledge_sources,
            "timestamp": now.isoformat(),
            "user": author,
            "report_version": current_version,
            "columns": exec_resp.columns,
            "rows": exec_resp.rows,
            "row_count": exec_resp.row_count,
            "kpis": kpi_metrics,
            "recommended_visualizations": analytics_recs,
            "report_data": report_data
        }

    @staticmethod
    def export_csv(report_data: ReportData) -> str:
        """Exports tabular report data to standard CSV format."""
        output = io.StringIO()
        if not report_data.data_columns:
            return ""

        writer = csv.DictWriter(output, fieldnames=report_data.data_columns)
        writer.writeheader()
        for row in report_data.data_rows:
            writer.writerow(row)
        return output.getvalue()

    @staticmethod
    def export_excel(report_data: ReportData) -> bytes:
        """Exports report to formatted multi-tab openpyxl Excel spreadsheet."""
        return ExcelReportExporter.generate_excel(report_data)

    @staticmethod
    def export_pdf(report_data: ReportData) -> bytes:
        """Exports report to boardroom-ready ReportLab PDF document."""
        return PDFReportExporter.generate_pdf(report_data)
