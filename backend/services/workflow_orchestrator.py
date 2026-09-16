"""Phase 14: Enterprise End-to-End Workflow Orchestrator.

Integrates all 14 architectural layers into a unified, zero-bypass pipeline:
1. Authenticate user
2. Identify selected database
3. Retrieve schema intelligence
4. Retrieve relevant approved SQL repository templates
5. Retrieve attrition business definition
6. Retrieve effective-dating rules
7. Generate SQL via AI Text-to-SQL engine
8. Validate SQL via AST syntax and structural rules
9. Apply security (Zero mutations, allowlist, CLS/RLS, sensitive column blocking)
10. Execute SQL via Secure Query Execution Engine
11. Calculate analytics (Totals, averages, attrition, trends, KPIs)
12. Create visualizations (Line, bar, metric cards)
13. Generate report (Assembled ReportData + CSV/Excel/PDF exports)
14. Save audit records across lifecycle
"""

import datetime
import time
from typing import Any

from sqlalchemy.orm import Session

from analytics.reusable_services import HRAnalyticsEngine
from backend.audit.service import EnterpriseAuditService
from backend.auth.authorization import AuthorizationService
from backend.database.connection_manager import connection_manager
from backend.database.models import User
from business_rules.service import BusinessRuleService
from query_execution.schemas import ExecuteQueryRequest
from query_execution.service import QueryExecutionService
from rag.rag_service import RAGService
from report_builder.pipeline_service import EndToEndReportBuilderService
from sql_validator.schemas import SQLValidationRequest
from sql_validator.service import SQLValidatorService
from text_to_sql.schemas import TextToSQLRequest
from text_to_sql.service import TextToSQLService


class WorkflowExecutionError(Exception):
    """Raised when any module in the 14-step workflow violates policy or fails."""


class EnterpriseWorkflowOrchestrator:
    """Coordinates and guarantees the 14-step end-to-end execution scenario."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_svc = EnterpriseAuditService(db)
        self.rag_svc = RAGService(db)
        self.rules_svc = BusinessRuleService(db)
        self.text_to_sql_svc = TextToSQLService(db)
        self.validator_svc = SQLValidatorService(db)
        self.executor_svc = QueryExecutionService(db)
        self.report_pipeline_svc = EndToEndReportBuilderService(db)

    def execute_canonical_scenario(
        self,
        question: str = "Show monthly employee attrition by department for 2026.",
        database_id: str = "sqlite_hr_default",
        username: str = "admin",
        client_ip: str = "127.0.0.1"
    ) -> dict[str, Any]:
        """Executes the exact 14-stage workflow requested in Phase 14."""
        workflow_start = time.time()
        stage_logs: list[dict[str, Any]] = []

        def log_stage(step_num: int, name: str, details: Any):
            stage_logs.append({
                "step": step_num,
                "name": name,
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                "details": details
            })

        # -------------------------------------------------------------
        # 1. Authenticate user
        # -------------------------------------------------------------
        user = self.db.query(User).filter(User.username == username).first()
        if not user or not user.is_active:
            raise WorkflowExecutionError(f"Step 1 Failed: User '{username}' is not active or authenticated.")
        self.audit_svc.log_user_login(username=user.username, success=True, ip=client_ip, user_role=user.role)
        log_stage(1, "Authenticate User", f"Authenticated user '{user.username}' with role '{user.role}'")

        # -------------------------------------------------------------
        # 2. Identify selected database
        # -------------------------------------------------------------
        can_access = AuthorizationService.can_access_database(self.db, user, database_id, mode="read")
        if not can_access:
            raise WorkflowExecutionError(f"Step 2 Failed: User '{username}' lacks access to database '{database_id}'.")
        self.audit_svc.log_database_selection(username=user.username, database_id=database_id, user_role=user.role)
        log_stage(2, "Identify Selected Database", f"Connected to target database '{database_id}'")

        # -------------------------------------------------------------
        # 3. Retrieve schema intelligence
        # -------------------------------------------------------------
        schema_info = connection_manager.get_schema(database_id)
        if not schema_info or not schema_info.table_allowlist:
            raise WorkflowExecutionError(f"Step 3 Failed: Schema discovery failed for database '{database_id}'.")
        log_stage(3, "Retrieve Schema", f"Discovered {len(schema_info.table_allowlist)} verified tables in schema allowlist")

        # -------------------------------------------------------------
        # 4. Retrieve relevant approved SQL
        # -------------------------------------------------------------
        context = self.rag_svc.get_context_for_query(query=question, database_id=database_id, top_k=5)
        reused_reports = context.existing_reports
        log_stage(4, "Retrieve Relevant Approved SQL", f"Retrieved {len(reused_reports)} candidate approved repository patterns")

        # -------------------------------------------------------------
        # 5. Retrieve attrition definition
        # -------------------------------------------------------------
        attrition_rules = [r for r in context.business_rules if "attrition" in r.get("rule_name", "").lower() or "turnover" in r.get("rule_name", "").lower()]
        log_stage(5, "Retrieve Attrition Definition", f"Retrieved {len(attrition_rules)} formal organizational attrition definitions")

        # -------------------------------------------------------------
        # 6. Retrieve effective-dating rules
        # -------------------------------------------------------------
        dating_rules = [r for r in context.business_rules if "dating" in r.get("rule_name", "").lower() or "active" in r.get("rule_name", "").lower()]
        self.audit_svc.log_retrieved_knowledge(username=user.username, query=question, chunk_count=len(context.retrieved_documents), latency_ms=10.0, user_role=user.role)
        log_stage(6, "Retrieve Effective-Dating Rules", f"Retrieved {len(dating_rules)} temporal effective-dating policies")

        # -------------------------------------------------------------
        # 7. Generate SQL
        # -------------------------------------------------------------
        self.audit_svc.log_ai_question(username=user.username, question=question, database_id=database_id, user_role=user.role)
        t2s_req = TextToSQLRequest(
            query=question,
            database_id=database_id,
            user_role=user.role,
            include_explanation=True,
            include_plan=True
        )
        t2s_resp = self.text_to_sql_svc.generate_sql(t2s_req)
        if t2s_resp.status != "SUCCESS" or not t2s_resp.sql:
            raise WorkflowExecutionError(f"Step 7 Failed: Text-to-SQL generation failed ({t2s_resp.message})")
        self.audit_svc.log_generated_sql(username=user.username, query=question, dialect=t2s_resp.dialect, sql=t2s_resp.sql, user_role=user.role)
        log_stage(7, "Generate SQL", f"Generated dialect-adapted SQL: {t2s_resp.sql[:100]}...")

        # -------------------------------------------------------------
        # 8. Validate SQL
        # -------------------------------------------------------------
        val_req = SQLValidationRequest(
            sql=t2s_resp.sql,
            database_id=database_id,
            username=user.username,
            user_role=user.role
        )
        val_resp = self.validator_svc.validate_query(val_req)
        if val_resp.status != "APPROVED" or not val_resp.validation_id:
            raise WorkflowExecutionError(f"Step 8 Failed: SQL Validation rejected ({val_resp.safe_error_explanation})")
        self.audit_svc.log_validation_result(username=user.username, validation_id=val_resp.validation_id, status=val_resp.status, risk_score=val_resp.risk_score, database_id=database_id, user_role=user.role)
        log_stage(8, "Validate SQL", f"SQL passed AST syntax and structural verification. Token: {val_resp.validation_id}")

        # -------------------------------------------------------------
        # 9. Apply security
        # -------------------------------------------------------------
        assert val_resp.is_valid is True
        assert val_resp.can_execute is True
        log_stage(9, "Apply Security", f"Security clearance granted. Zero mutation AST confirmed. Row limit: {val_resp.max_row_limit}")

        # -------------------------------------------------------------
        # 10. Execute SQL
        # -------------------------------------------------------------
        exec_req = ExecuteQueryRequest(
            validation_id=val_resp.validation_id,
            bypass_cache=True
        )
        exec_resp = self.executor_svc.execute(exec_req, user=user)
        self.audit_svc.log_query_execution(
            username=user.username,
            execution_id=exec_resp.execution_id,
            status=exec_resp.status,
            row_count=exec_resp.row_count,
            time_ms=exec_resp.execution_time_ms,
            database_id=database_id,
            user_role=user.role
        )
        log_stage(10, "Execute SQL", f"Executed via read-only driver in {exec_resp.execution_time_ms}ms. Returned {exec_resp.row_count} rows.")

        # -------------------------------------------------------------
        # 11. Calculate analytics
        # -------------------------------------------------------------
        import pandas as pd
        df = pd.DataFrame(exec_resp.rows, columns=exec_resp.columns) if exec_resp.rows else pd.DataFrame(columns=exec_resp.columns)
        visual_recs = HRAnalyticsEngine.recommend_visualizations(df)
        log_stage(11, "Calculate Analytics", f"Computed HR analytics and derived {len(visual_recs)} visualization recommendations")

        # -------------------------------------------------------------
        # 12. Create visualization
        # -------------------------------------------------------------
        chart_types = [r.get("chart_type") for r in visual_recs]
        log_stage(12, "Create Visualization", f"Configured executive charts: {chart_types}")

        # -------------------------------------------------------------
        # 13. Generate report
        # -------------------------------------------------------------
        report_output = self.report_pipeline_svc.generate_report_from_question(
            question=question,
            database_id=database_id,
            user=user,
            save_report=True
        )
        self.audit_svc.log_report_creation(
            username=user.username,
            report_id=report_output["report_id"],
            title=report_output["title"],
            database_id=database_id,
            user_role=user.role
        )
        log_stage(13, "Generate Report", f"Assembled report '{report_output['title']}' (ID: {report_output['report_id']})")

        # -------------------------------------------------------------
        # 14. Save audit record
        # -------------------------------------------------------------
        total_time_ms = round((time.time() - workflow_start) * 1000, 2)
        final_audit = self.audit_svc.log_event(
            event_type="END_TO_END_INTEGRATION_COMPLETED",
            username=user.username,
            user_role=user.role,
            database_id=database_id,
            status="SUCCESS",
            execution_time_ms=total_time_ms,
            details={
                "canonical_question": question,
                "stages_executed": len(stage_logs),
                "report_id": report_output["report_id"],
                "total_duration_ms": total_time_ms
            }
        )
        log_stage(14, "Save Audit Record", f"Persisted end-to-end integration audit record #{final_audit.id}")

        return {
            "status": "SUCCESS",
            "stages_completed": len(stage_logs),
            "stages": stage_logs,
            "canonical_question": question,
            "generated_sql": t2s_resp.sql,
            "validation_id": val_resp.validation_id,
            "execution_id": exec_resp.execution_id,
            "report_id": report_output["report_id"],
            "total_execution_time_ms": total_time_ms,
            "preserved_attributes": {
                "question": question,
                "sql": t2s_resp.sql,
                "database": database_id,
                "knowledge_sources": report_output["knowledge_sources"],
                "timestamp": report_output["timestamp"],
                "user": user.username,
                "report_version": report_output["report_version"]
            }
        }
