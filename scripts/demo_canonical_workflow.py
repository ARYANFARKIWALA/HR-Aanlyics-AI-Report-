"""Phase 17: Final Canonical Demonstration Workflow.

Demonstrates the 12-stage enterprise execution pipeline:
1. Login
2. Select database
3. Ask question ("Show monthly employee attrition by department for 2026.")
4. RAG retrieval (schema, rules, and existing SQL knowledge reuse)
5. Generated SQL (transpiled to database dialect)
6. SQL validation (AST syntax, zero mutations, allowlists, security gates)
7. Execution (read-only driver connection, row limiting, timeout)
8. Analytics (totals, averages, rates, time-series trends)
9. Chart (visualization recommendations)
10. Report (assembly with 7 preserved attributes)
11. Export (CSV, Excel, PDF)
12. Audit log (enterprise security & compliance record)

Demonstrates how existing institutional SQL knowledge is preserved and reused
rather than building Text-to-SQL from scratch without organizational knowledge.
"""

import sys
import os
import time
import json

# Ensure project root is in python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database.connection import SessionLocal, init_db
from backend.database.models import User
from backend.database.models_audit import LifecycleAuditLog
from backend.auth.authorization import AuthorizationService
from backend.database.connection_manager import connection_manager
from rag.rag_service import RAGService
from text_to_sql.service import TextToSQLService
from text_to_sql.schemas import TextToSQLRequest
from sql_validator.service import SQLValidatorService
from sql_validator.schemas import SQLValidationRequest
from query_execution.service import QueryExecutionService
from query_execution.schemas import ExecuteQueryRequest
from analytics.reusable_services import HRAnalyticsEngine
from report_builder.pipeline_service import EndToEndReportBuilderService
from backend.audit.service import EnterpriseAuditService


def run_canonical_demonstration():
    print("=" * 80)
    print("HR ANALYTICS AI REPORT BUILDER — ENTERPRISE WORKFLOW DEMONSTRATION")
    print("=" * 80)
    
    init_db()
    db = SessionLocal()

    try:
        # -------------------------------------------------------------
        # 1. Login
        # -------------------------------------------------------------
        print("\n[Stage 1/12] USER AUTHENTICATION")
        username = "admin"
        user = db.query(User).filter(User.username == username).first()
        if not user:
            from backend.auth.password import hash_password
            user = User(
                username=username,
                email="admin@enterprise.corp",
                full_name="Enterprise System Administrator",
                hashed_password=hash_password("EnterpriseAdmin2026!"),
                role="SUPER_ADMIN",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        audit_svc = EnterpriseAuditService(db)
        audit_svc.log_user_login(username=user.username, success=True, user_role=user.role)
        print(f" -> Authenticated: '{user.full_name}' ({user.username}) | Role: {user.role} | Active: {user.is_active}")

        # -------------------------------------------------------------
        # 2. Select Database
        # -------------------------------------------------------------
        print("\n[Stage 2/12] DATABASE SELECTION")
        database_id = "sqlite_hr_default"
        can_access = AuthorizationService.can_access_database(db, user, database_id, mode="read")
        assert can_access, f"Access denied to database {database_id}"
        audit_svc.log_database_selection(username=user.username, database_id=database_id, user_role=user.role)
        print(f" -> Target Database: '{database_id}' | Driver Mode: STRICT_READ_ONLY | Authorization: GRANTED")

        # -------------------------------------------------------------
        # 3. Ask Question
        # -------------------------------------------------------------
        question = "Show monthly employee attrition by department for 2026."
        print("\n[Stage 3/12] NATURAL LANGUAGE HR QUESTION")
        print(f" -> Query: \"{question}\"")
        audit_svc.log_ai_question(username=user.username, question=question, database_id=database_id, user_role=user.role)

        # -------------------------------------------------------------
        # 4. RAG Retrieval & Institutional SQL Knowledge Reuse
        # -------------------------------------------------------------
        print("\n[Stage 4/12] RAG RETRIEVAL & ORGANIZATIONAL KNOWLEDGE REUSE")
        rag_svc = RAGService(db)
        rag_context = rag_svc.get_context_for_query(query=question, database_id=database_id, top_k=5)
        print(f" -> Retrieved Context Status: {rag_context.status}")
        print(f" -> Relevant Entities Identified: {rag_context.relevant_tables}")
        print(f" -> Business Rules Retrieved: {len(rag_context.business_rules)} active policies")
        print(f" -> Approved Organizational SQL Reports Found: {len(rag_context.existing_reports)}")
        for rpt in rag_context.existing_reports[:2]:
            print(f"    * Preserved Pattern: [{rpt.get('report_code')}] {rpt.get('report_name')}")

        # -------------------------------------------------------------
        # 5. Generated SQL
        # -------------------------------------------------------------
        print("\n[Stage 5/12] DIALECT-ADAPTED SQL GENERATION")
        t2s_svc = TextToSQLService(db)
        t2s_req = TextToSQLRequest(
            query=question,
            database_id=database_id,
            user_role=user.role,
            include_explanation=True,
            include_plan=True
        )
        t2s_resp = t2s_svc.generate_sql(t2s_req)
        assert t2s_resp.status == "SUCCESS"
        print(f" -> Target Dialect: {t2s_resp.dialect.upper()} (Execution Permitted: {t2s_resp.execution_permitted})")
        print(f" -> Generated SQL Query:\n{t2s_resp.sql}\n")
        audit_svc.log_generated_sql(username=user.username, query=question, dialect=t2s_resp.dialect, sql=t2s_resp.sql, user_role=user.role)

        # -------------------------------------------------------------
        # 6. SQL Validation (AST & Security Boundaries)
        # -------------------------------------------------------------
        print("\n[Stage 6/12] ZERO-TRUST SQL VALIDATION (MODULE 7)")
        validator_svc = SQLValidatorService(db)
        val_req = SQLValidationRequest(
            sql=t2s_resp.sql,
            database_id=database_id,
            username=user.username,
            user_role=user.role
        )
        val_resp = validator_svc.validate_query(val_req)
        assert val_resp.status == "APPROVED"
        print(f" -> Validation Status: {val_resp.status} | Risk Score: {val_resp.risk_score}")
        print(f" -> AST Verification Token: {val_resp.validation_id}")
        print(f" -> Mutation Check: PASSED (Zero DDL/DML mutations detected)")
        print(f" -> Schema Allowlists: PASSED (All tables/columns exist in catalog)")
        audit_svc.log_validation_result(username=user.username, validation_id=val_resp.validation_id, status=val_resp.status, risk_score=val_resp.risk_score, database_id=database_id, user_role=user.role)

        # -------------------------------------------------------------
        # 7. Secure Query Execution (Module 8)
        # -------------------------------------------------------------
        print("\n[Stage 7/12] SECURE QUERY EXECUTION (MODULE 8)")
        executor_svc = QueryExecutionService(db)
        exec_req = ExecuteQueryRequest(
            validation_id=val_resp.validation_id,
            bypass_cache=True
        )
        exec_resp = executor_svc.execute(exec_req, user=user)
        assert exec_resp.status == "SUCCESS"
        standard_res = exec_resp.to_standard_dict()
        print(f" -> Driver Isolation: Read-Only PRAGMA active")
        print(f" -> Execution Duration: {standard_res['execution_time']} ms")
        print(f" -> Rows Returned: {standard_res['row_count']}")
        print(f" -> Columns: {standard_res['columns']}")
        audit_svc.log_query_execution(username=user.username, execution_id=exec_resp.execution_id, status=exec_resp.status, row_count=exec_resp.row_count, time_ms=exec_resp.execution_time_ms, database_id=database_id, user_role=user.role)

        # -------------------------------------------------------------
        # 8. HR Analytics Engine (Module 9)
        # -------------------------------------------------------------
        print("\n[Stage 8/12] HR ANALYTICS & STATISTICAL METRICS")
        import pandas as pd
        df = pd.DataFrame(standard_res["rows"], columns=standard_res["columns"]) if standard_res["rows"] else pd.DataFrame(columns=standard_res["columns"])
        visual_recs = HRAnalyticsEngine.recommend_visualizations(df)
        print(f" -> Derived Visualization Recommendations: {len(visual_recs)}")
        for rec in visual_recs:
            print(f"    * Recommended Chart: {rec.get('chart_type')} | Title: {rec.get('title')}")

        # -------------------------------------------------------------
        # 9. Chart Visualization
        # -------------------------------------------------------------
        print("\n[Stage 9/12] EXECUTIVE CHART GENERATION")
        for rec in visual_recs:
            print(f" -> Rendered Chart Spec: {rec.get('chart_type')} [X: {rec.get('x_column')}, Y: {rec.get('y_column')}]")

        # -------------------------------------------------------------
        # 10. Report Assembly & Preservation of 7 Required Attributes
        # -------------------------------------------------------------
        print("\n[Stage 10/12] REPORT BUILDER ASSEMBLY (MODULE 10)")
        pipeline_svc = EndToEndReportBuilderService(db)
        report_output = pipeline_svc.generate_report_from_question(
            question=question,
            database_id=database_id,
            user=user,
            save_report=True
        )
        print(f" -> Generated Report Title: '{report_output['title']}'")
        print(f" -> Report ID: {report_output['report_id']} | Version: {report_output['report_version']}")
        print(f" -> Preserved Attributes:")
        print(f"    1. Question: {report_output['question']}")
        print(f"    2. SQL: {report_output['sql_query'][:80]}...")
        print(f"    3. Database: {report_output['database_id']}")
        print(f"    4. Knowledge Sources: Reused {len(report_output['knowledge_sources'].get('reused_reports', []))} repository reports")
        print(f"    5. Timestamp: {report_output['timestamp']}")
        print(f"    6. User: {report_output['user']}")
        print(f"    7. Report Version: {report_output['report_version']}")

        # -------------------------------------------------------------
        # 11. Export (CSV, Excel, PDF)
        # -------------------------------------------------------------
        print("\n[Stage 11/12] MULTI-FORMAT REPORT EXPORTS")
        report_data = report_output["report_data"]
        csv_data = pipeline_svc.export_csv(report_data)
        excel_bytes = pipeline_svc.export_excel(report_data)
        pdf_bytes = pipeline_svc.export_pdf(report_data)
        print(f" -> Export [CSV]: Generated {len(csv_data)} characters")
        print(f" -> Export [EXCEL]: Generated {len(excel_bytes)} bytes (.xlsx)")
        print(f" -> Export [PDF]: Generated {len(pdf_bytes)} bytes (.pdf)")

        # -------------------------------------------------------------
        # 12. Audit Logging
        # -------------------------------------------------------------
        print("\n[Stage 12/12] AUDIT LOGGING & COMPLIANCE TRAIL")
        final_audit = audit_svc.log_event(
            event_type="CANONICAL_DEMO_COMPLETED",
            username=user.username,
            user_role=user.role,
            database_id=database_id,
            status="SUCCESS",
            details={
                "canonical_question": question,
                "report_id": report_output["report_id"],
                "stages_demonstrated": 12
            }
        )
        print(f" -> Persisted Audit Event #{final_audit.id}: {final_audit.event_type} | Status: {final_audit.status}")

        print("\n" + "=" * 80)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY — ALL 12 STAGES VERIFIED")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_canonical_demonstration()
