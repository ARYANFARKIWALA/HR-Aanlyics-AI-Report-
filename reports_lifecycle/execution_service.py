"""Execution pipeline enforcing the Re-run Revalidation Invariant for Module 12."""

import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from backend.database.models import User
from backend.database.models_reports import SavedReport, ReportExecutionRecord
from sql_validator.service import SQLValidatorService
from sql_validator.schemas import SQLValidationRequest
from query_execution.service import QueryExecutionService
from query_execution.schemas import ExecuteQueryRequest
from .schemas import ReportRunRequest, ReportRunResponse
from .version_service import ReportVersionService


class ReportExecutionService:
    """Orchestrates secure re-run of reports via Module 7 validator and Module 8 execution."""

    @classmethod
    def run_report(
        cls,
        db: Session,
        report: SavedReport,
        user: User,
        run_req: Optional[ReportRunRequest] = None
    ) -> ReportRunResponse:
        """Executes a report while strictly maintaining the Re-run Revalidation Invariant.
        
        Raw SQL is NEVER executed directly. It MUST pass through Module 7 validation first,
        receive an approved cryptographic token, and execute only through Module 8.
        """
        # Determine SQL to execute (current or specific historical version)
        sql_to_run = report.sql_query
        if run_req and run_req.version_number:
            ver = ReportVersionService.get_version(db, report, run_req.version_number)
            if not ver:
                raise ValueError(f"Version {run_req.version_number} not found for report {report.report_id}")
            sql_to_run = ver.sql_query

        target_db = (run_req.database_id if run_req and run_req.database_id else report.database_id) or "sqlite_hr_default"

        # Step 1: Module 7 - SQL Validator & Security Gate
        validator_svc = SQLValidatorService(db=db)
        val_req = SQLValidationRequest(
            sql=sql_to_run,
            database_id=target_db,
            user_id=user.id if user else None,
            user_role=getattr(user, "role", "hr_analyst")
        )
        val_res = validator_svc.validate_query(val_req)

        if val_res.status != "APPROVED":
            err_msg = f"SQL Validation failed with status {val_res.status}: {'; '.join(val_res.violations or ['Risk policy violated'])}"
            # Record failed execution attempt
            rec = ReportExecutionRecord(
                saved_report_id=report.id,
                execution_id=f"exec_val_fail_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                validation_id=val_res.validation_id or "NONE",
                user_id=user.id if user else None,
                username=user.username if user else "anonymous",
                status="VALIDATION_FAILED",
                row_count=0,
                duration_ms=0.0,
                created_at=datetime.datetime.now(datetime.UTC)
            )
            db.add(rec)
            db.commit()

            return ReportRunResponse(
                report_id=report.report_id,
                execution_id=rec.execution_id,
                validation_id=val_res.validation_id or "NONE",
                status="VALIDATION_FAILED",
                columns=[],
                rows=[],
                row_count=0,
                duration_ms=0.0,
                error=err_msg
            )

        # Step 2: Module 8 - Query Execution Engine Handshake
        exec_svc = QueryExecutionService(db=db)
        page_sz = min(run_req.limit, 1000) if (run_req and run_req.limit) else 1000
        exec_req = ExecuteQueryRequest(
            validation_id=val_res.validation_id,
            page_size=page_sz,
            bypass_cache=False
        )
        exec_res = exec_svc.execute(exec_req, user=user)

        exec_time = getattr(exec_res, "execution_time_ms", 0.0)
        err_msg = getattr(exec_res, "error_message", None)
        is_truncated = getattr(exec_res, "total_rows", 0) > len(exec_res.rows)

        # Step 3: Record execution in report history
        rec = ReportExecutionRecord(
            saved_report_id=report.id,
            execution_id=exec_res.execution_id,
            validation_id=val_res.validation_id,
            user_id=user.id if user else None,
            username=user.username if user else "anonymous",
            status=exec_res.status,
            row_count=exec_res.total_rows,
            duration_ms=exec_time,
            created_at=datetime.datetime.now(datetime.UTC)
        )
        db.add(rec)
        db.commit()

        return ReportRunResponse(
            report_id=report.report_id,
            execution_id=exec_res.execution_id,
            validation_id=val_res.validation_id,
            status=exec_res.status,
            columns=exec_res.columns,
            rows=exec_res.rows,
            row_count=exec_res.total_rows,
            duration_ms=exec_time,
            cached=exec_res.cached,
            truncated=is_truncated,
            error=err_msg
        )

    @classmethod
    def list_executions(
        cls,
        db: Session,
        report: SavedReport,
        limit: int = 50
    ) -> List[ReportExecutionRecord]:
        """Lists historical executions for a report, most recent first."""
        return db.query(ReportExecutionRecord).filter(
            ReportExecutionRecord.saved_report_id == report.id
        ).order_by(ReportExecutionRecord.created_at.desc()).limit(limit).all()
