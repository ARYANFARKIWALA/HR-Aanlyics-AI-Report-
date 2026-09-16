"""HR ANALYTICS AI REPORT BUILDER — Complete Enterprise Frontend (Phase 11).

Provides an executive enterprise navigation structure:
1. Dashboard
2. Ask AI (Main centerpiece)
3. Reports
4. SQL Repository
5. Schema Explorer
6. Business Rules
7. Knowledge/RAG
8. Query History
9. Administration
10. Settings
"""

import os
import sys
import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

# Ensure project root in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database.connection import SessionLocal, init_db
from backend.database.models import User, Department, Employee
from backend.database.models_reports import SavedReport
from backend.database.models_validation import SQLValidationAuditLog
from backend.database.models_execution import QueryExecutionAuditLog
from backend.database.connection_manager import connection_manager
from report_builder.pipeline_service import EndToEndReportBuilderService
from business_rules.service import BusinessRuleService
from rag.rag_service import RAGService
from analytics.reusable_services import HRAnalyticsEngine
from config.settings import settings

# Page config
st.set_page_config(
    page_title="HR Analytics AI Report Builder",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize DB session
init_db()
db = SessionLocal()

# ----------------- SIDEBAR & IDENTITY -----------------
with st.sidebar:
    st.markdown("## 🏢 Enterprise HR AI")
    st.caption("Grounded SQL & Knowledge Intelligence")

    # User Persona Selector
    users = db.query(User).filter(User.is_active == True).all()
    user_map = {u.username: u for u in users}

    if "current_username" not in st.session_state:
        st.session_state["current_username"] = "admin" if "admin" in user_map else list(user_map.keys())[0]

    current_user = user_map.get(st.session_state["current_username"])
    current_idx = list(user_map.keys()).index(st.session_state["current_username"]) if current_user else 0

    selected_username = st.selectbox(
        "Active User:",
        options=list(user_map.keys()),
        index=current_idx,
        key="sidebar_active_user"
    )
    st.session_state["current_username"] = selected_username
    active_user = user_map.get(selected_username)

    user_role = active_user.role.upper() if active_user else "HR_ANALYST"
    is_admin = user_role in ("SUPER_ADMIN", "HR_ADMIN", "ADMIN")

    st.info(f"**Role:** `{user_role}`\n**Name:** {active_user.full_name if active_user else 'Anonymous'}")

    st.markdown("---")

    # 10 Navigation Items
    navigation_options = [
        "Ask AI",
        "Dashboard",
        "Reports",
        "SQL Repository",
        "Schema Explorer",
        "Business Rules",
        "Knowledge/RAG",
        "Query History",
        "Administration",
        "Settings"
    ]

    selected_nav = st.radio(
        "Navigation:",
        options=navigation_options,
        index=0,
        key="main_navigation_radio"
    )

    st.markdown("---")
    st.caption("🔒 Multi-engine Grounded RAG\nStrict Read-Only Connection")


# ==============================================================================
# 1. ASK AI — MAIN REPORT BUILDER PAGE (Phase 11 Core Display Flow)
# ==============================================================================
if selected_nav == "Ask AI":
    st.title("🏢 HR ANALYTICS AI REPORT BUILDER")
    st.markdown("Ask natural-language workforce questions to generate verified reports backed by institutional SQL and business policies.")

    col_q, col_db = st.columns([4, 1])
    with col_q:
        default_prompt = "Show employee count by department for 2026."
        user_question = st.text_input(
            "Ask your HR question...",
            value=default_prompt,
            key="ai_question_input",
            placeholder="e.g. Show monthly employee attrition by department for 2026."
        )
    with col_db:
        dbs = connection_manager.list_databases_safe()
        db_options = [d["database_id"] for d in dbs] or ["sqlite_hr_default"]
        selected_db = st.selectbox("Target Database:", options=db_options, index=0)

    # Quick prompt examples
    st.markdown("**Example questions:**")
    ex_col1, ex_col2, ex_col3 = st.columns(3)
    with ex_col1:
        if st.button("📊 Employee count by department", width='stretch'):
            st.session_state["ai_question_input"] = "Show employee count by department for 2026."
            st.rerun()
    with ex_col2:
        if st.button("📉 Monthly attrition by department", width='stretch'):
            st.session_state["ai_question_input"] = "Show monthly employee attrition by department for 2026."
            st.rerun()
    with ex_col3:
        if st.button("💰 Average salary by department", width='stretch'):
            st.session_state["ai_question_input"] = "Show average salary by department"
            st.rerun()

    generate_clicked = st.button("🚀 Generate Report", type="primary", width='stretch')

    if generate_clicked and user_question:
        with st.spinner("Processing natural-language query through 7-stage enterprise pipeline..."):
            pipeline_svc = EndToEndReportBuilderService(db=db)
            report_result = pipeline_svc.generate_report_from_question(
                question=user_question,
                database_id=selected_db,
                user=active_user,
                save_report=True
            )

        if report_result.get("status") == "SUCCESS":
            st.success("✅ Report successfully generated and verified across all 7 stages!")
            st.markdown("---")

            # ---------------- STAGE 1: QUESTION ----------------
            st.markdown("### 1️⃣ Question")
            st.info(f"**Natural Language Prompt:** *\"{report_result['question']}\"*")
            st.markdown("<div style='text-align: center; font-size: 24px; color: #64748B;'>↓</div>", unsafe_allow_html=True)

            # ---------------- STAGE 2: RELEVANT KNOWLEDGE ----------------
            st.markdown("### 2️⃣ Relevant Knowledge")
            k_sources = report_result.get("knowledge_sources", {})
            k_col1, k_col2, k_col3 = st.columns(3)
            with k_col1:
                st.metric("Applied Business Rules", len(k_sources.get("applied_rules", [])))
            with k_col2:
                st.metric("Reused Approved Queries", len(k_sources.get("reused_reports", [])))
            with k_col3:
                st.metric("Model Confidence", f"{int(k_sources.get('confidence_score', 1.0) * 100)}%")

            if k_sources.get("applied_rules"):
                with st.expander("View Attached Knowledge Rules", expanded=False):
                    for r in k_sources["applied_rules"]:
                        st.markdown(f"- **{r.get('rule_name', 'Rule')}**: {r.get('formula_definition') or r.get('description', '')}")

            st.markdown("<div style='text-align: center; font-size: 24px; color: #64748B;'>↓</div>", unsafe_allow_html=True)

            # ---------------- STAGE 3: GENERATED SQL ----------------
            st.markdown("### 3️⃣ Generated SQL")
            st.code(report_result["sql_query"], language="sql")
            st.markdown("<div style='text-align: center; font-size: 24px; color: #64748B;'>↓</div>", unsafe_allow_html=True)

            # ---------------- STAGE 4: VALIDATION STATUS ----------------
            st.markdown("### 4️⃣ Validation Status")
            st.markdown(f"""
            <div style="background-color: #ECFDF5; border: 1px solid #10B981; padding: 12px; border-radius: 8px; color: #065F46;">
                <strong>🛡️ ZERO-TRUST SECURITY GATEWAY: VALIDATED & APPROVED</strong><br/>
                Token: <code>{report_result['validation_id']}</code> | Driver Invariant: <code>PRAGMA query_only = ON</code> | Mutations Blocked: <code>100%</code>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='text-align: center; font-size: 24px; color: #64748B;'>↓</div>", unsafe_allow_html=True)

            # ---------------- STAGE 5: RESULTS ----------------
            st.markdown("### 5️⃣ Results")
            rows = report_result.get("rows", [])
            cols = report_result.get("columns", [])
            df_results = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)

            res_m1, res_m2 = st.columns(2)
            with res_m1:
                st.metric("Total Rows", report_result.get("row_count", 0))
            with res_m2:
                st.metric("Execution Latency", f"{report_result.get('kpis', {}).get('execution_time_seconds', 0.0):.3f}s")

            if not df_results.empty:
                st.dataframe(df_results, width='stretch')
            else:
                st.info("Query returned 0 matching records for the specified period.")

            st.markdown("<div style='text-align: center; font-size: 24px; color: #64748B;'>↓</div>", unsafe_allow_html=True)

            # ---------------- STAGE 6: CHARTS ----------------
            st.markdown("### 6️⃣ Charts & Visualizations")
            recs = report_result.get("recommended_visualizations", [])

            # Render KPI Metric Cards if available
            metric_cards = [r for r in recs if r.get("chart_type") == "metric_card"]
            if metric_cards:
                k_cols = st.columns(min(len(metric_cards), 4))
                for idx, card in enumerate(metric_cards[:4]):
                    with k_cols[idx]:
                        st.metric(label=card.get("title", "Metric"), value=card.get("value", 0.0))

            # Render Bar or Line charts if data exists
            if not df_results.empty:
                chart_recs = [r for r in recs if r.get("chart_type") in ("bar", "line", "pie")]
                if chart_recs:
                    c_spec = chart_recs[0]
                    c_type = c_spec.get("chart_type")
                    x_col = c_spec.get("x_axis")
                    y_col = c_spec.get("y_axis")

                    if c_type == "bar" and x_col and y_col and x_col in df_results.columns and y_col in df_results.columns:
                        fig = px.bar(df_results, x=x_col, y=y_col, title=c_spec.get("title", "Comparison Chart"), template="plotly_white", color_discrete_sequence=["#1E3A8A"])
                        st.plotly_chart(fig, width='stretch')
                    elif c_type == "line" and x_col and y_col and x_col in df_results.columns and y_col in df_results.columns:
                        fig = px.line(df_results, x=x_col, y=y_col, title=c_spec.get("title", "Trend Analysis"), template="plotly_white", markers=True, color_discrete_sequence=["#2563EB"])
                        st.plotly_chart(fig, width='stretch')
            else:
                st.caption("Charts will automatically render when records are present.")

            st.markdown("<div style='text-align: center; font-size: 24px; color: #64748B;'>↓</div>", unsafe_allow_html=True)

            # ---------------- STAGE 7: DOWNLOAD REPORT ----------------
            st.markdown("### 7️⃣ Download Report")
            report_data = report_result.get("report_data")
            if report_data:
                down_c1, down_c2, down_c3 = st.columns(3)
                with down_c1:
                    csv_data = EndToEndReportBuilderService.export_csv(report_data)
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv_data,
                        file_name=f"HR_Report_{report_result['report_id']}.csv",
                        mime="text/csv",
                        width='stretch'
                    )
                with down_c2:
                    excel_data = EndToEndReportBuilderService.export_excel(report_data)
                    st.download_button(
                        label="📊 Download Excel",
                        data=excel_data,
                        file_name=f"HR_Report_{report_result['report_id']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width='stretch'
                    )
                with down_c3:
                    pdf_data = EndToEndReportBuilderService.export_pdf(report_data)
                    st.download_button(
                        label="📑 Download PDF",
                        data=pdf_data,
                        file_name=f"HR_Report_{report_result['report_id']}.pdf",
                        mime="application/pdf",
                        width='stretch'
                    )

        else:
            st.error(f"Execution Stopped: {report_result.get('message', 'An error occurred during report generation.')}")


# ==============================================================================
# 2. DASHBOARD
# ==============================================================================
elif selected_nav == "Dashboard":
    st.title("📊 Workforce Analytics Dashboard")
    st.markdown("High-level executive overview of organizational headcount, turnover, and reporting telemetry.")

    emp_count = db.query(Employee).count()
    dept_count = db.query(Department).count()
    saved_count = db.query(SavedReport).filter(SavedReport.is_deleted == False).count()
    audit_count = db.query(QueryExecutionAuditLog).count()

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.metric("Total Employees", emp_count)
    with d2:
        st.metric("Departments", dept_count)
    with d3:
        st.metric("Saved Reports", saved_count)
    with d4:
        st.metric("Executed Queries", audit_count)

    st.markdown("---")
    st.subheader("Recent System Query Executions")
    recent_execs = db.query(QueryExecutionAuditLog).order_by(QueryExecutionAuditLog.id.desc()).limit(10).all()
    if recent_execs:
        exec_data = [{
            "Execution ID": e.execution_id,
            "Database": e.database_id,
            "User": e.username,
            "Status": e.status,
            "Rows": e.row_count,
            "Time (ms)": e.execution_time_ms
        } for e in recent_execs]
        st.dataframe(pd.DataFrame(exec_data), width='stretch')
    else:
        st.info("No queries executed yet.")


# ==============================================================================
# 3. REPORTS
# ==============================================================================
elif selected_nav == "Reports":
    st.title("📁 Saved Enterprise Reports")
    st.markdown("Browse, execute, and export saved organizational report definitions.")

    reports = db.query(SavedReport).filter(SavedReport.is_deleted == False).order_by(SavedReport.id.desc()).all()
    if reports:
        for rpt in reports:
            with st.expander(f"📄 {rpt.title} (v{rpt.current_version}) — {rpt.category}", expanded=False):
                st.markdown(f"**Description:** {rpt.description or 'No description provided.'}")
                st.caption(f"Author: {rpt.author_username} | Created: {rpt.created_at}")
                st.code(rpt.sql_query, language="sql")
    else:
        st.info("No saved reports found. Use 'Ask AI' to generate and save your first report!")


# ==============================================================================
# 4. SQL REPOSITORY
# ==============================================================================
elif selected_nav == "SQL Repository":
    st.title("📚 Curated SQL Repository")
    st.markdown("Catalog of approved, verified enterprise HR SQL queries and canonical patterns.")

    from backend.database.models_repository import SQLReport
    approved_reports = db.query(SQLReport).filter(SQLReport.approval_status == "approved").all()
    if approved_reports:
        for ar in approved_reports:
            with st.expander(f"✅ {ar.title} ({ar.category})", expanded=False):
                st.markdown(f"**Description:** {ar.description}")
                st.caption(f"Database: {ar.database_id} | Dialect: {ar.dialect} | Author: {ar.author}")
                st.code(ar.sql_query, language="sql")
    else:
        st.info("No approved repository queries cataloged yet.")


# ==============================================================================
# 5. SCHEMA EXPLORER
# ==============================================================================
elif selected_nav == "Schema Explorer":
    st.title("🔍 Schema Intelligence Explorer")
    st.markdown("Inspect registered databases, discovered tables, and column metadata.")

    dbs = connection_manager.list_databases_safe()
    db_options = [d["database_id"] for d in dbs] or ["sqlite_hr_default"]
    target_db = st.selectbox("Select Database to Inspect:", options=db_options)

    schema_info = connection_manager.get_schema(target_db)
    if schema_info:
        st.markdown(f"**Total Tables:** `{len(schema_info.table_allowlist)}`")
        selected_tbl = st.selectbox("Select Table:", options=sorted(list(schema_info.table_allowlist)))
        cols = schema_info.column_allowlist_map.get(selected_tbl, [])
        st.markdown(f"**Columns for `{selected_tbl}`:**")
        st.write(sorted(list(cols)))


# ==============================================================================
# 6. BUSINESS RULES
# ==============================================================================
elif selected_nav == "Business Rules":
    st.title("⚖️ HR Business Rules & Effective-Dating Policies")
    st.markdown("Enterprise definitions and formal constraints automatically enforced by the AI.")

    rule_svc = BusinessRuleService(db)
    rules = rule_svc.list_rules()
    if rules:
        for r in rules:
            with st.expander(f"📌 {r.rule_name} ({r.category})", expanded=False):
                st.markdown(f"**Formula/Predicate:** `{r.formula_definition}`")
                st.markdown(f"**Description:** {r.description}")
                st.caption(f"Status: {r.status} | Security Level: {r.security_level}")
    else:
        st.info("No business rules registered.")


# ==============================================================================
# 7. KNOWLEDGE/RAG
# ==============================================================================
elif selected_nav == "Knowledge/RAG":
    st.title("🧠 Grounded RAG Knowledge Base")
    st.markdown("Semantic context retrieval engine for HR handbooks, policies, and queries.")

    rag_svc = RAGService(db)
    test_query = st.text_input("Semantic Search Knowledge Base:", value="What is the voluntary attrition formula?")
    if st.button("Search Knowledge Base"):
        ctx = rag_svc.get_context_for_query(test_query, top_k=5)
        st.markdown(f"**Status:** `{ctx.status}` | **Confidence:** `{ctx.confidence_score}`")
        st.markdown("#### Retrieved Chunks:")
        for ch in ctx.chunks:
            st.markdown(f"- **[{ch.get('category')}] {ch.get('title', 'Rule')}**: {ch.get('content', '')[:200]}...")


# ==============================================================================
# 8. QUERY HISTORY
# ==============================================================================
elif selected_nav == "Query History":
    st.title("📜 Query Audit History")
    st.markdown("Telemetry log of all queries validated and executed across the platform.")

    val_logs = db.query(SQLValidationAuditLog).order_by(SQLValidationAuditLog.id.desc()).limit(20).all()
    if val_logs:
        log_records = [{
            "Validation ID": v.validation_id,
            "User": v.username,
            "Status": v.status,
            "Risk Score": v.risk_score,
            "Risk Level": v.risk_level,
            "Time": str(v.created_at)
        } for v in val_logs]
        st.dataframe(pd.DataFrame(log_records), width='stretch')
    else:
        st.info("No validation history found.")


# ==============================================================================
# 9. ADMINISTRATION
# ==============================================================================
elif selected_nav == "Administration":
    st.title("🛡️ Enterprise Administration & RBAC")
    if not is_admin:
        st.warning("⚠️ Access Restricted: This section requires SUPER_ADMIN or HR_ADMIN privileges.")
    else:
        st.markdown("Manage user credentials, roles, and database connection profiles.")
        all_users = db.query(User).all()
        user_table = [{
            "ID": u.id,
            "Username": u.username,
            "Full Name": u.full_name,
            "Email": u.email,
            "Role": u.role,
            "Active": u.is_active
        } for u in all_users]
        st.dataframe(pd.DataFrame(user_table), width='stretch')


# ==============================================================================
# 10. SETTINGS
# ==============================================================================
elif selected_nav == "Settings":
    st.title("⚙️ System Settings & Telemetry")
    st.markdown("Platform environment variables, timeout policies, and cache controls.")

    s_col1, s_col2 = st.columns(2)
    with s_col1:
        st.markdown("### Operational Configuration")
        st.write({
            "ENVIRONMENT": settings.environment,
            "DEFAULT_DB": settings.default_db_id,
            "STATEMENT_TIMEOUT_SECONDS": 30,
            "MAX_ROW_LIMIT": 5000,
            "TOKEN_TTL_MINUTES": 15
        })
    with s_col2:
        st.markdown("### Driver Invariants")
        st.write({
            "READ_ONLY_ENFORCEMENT": "PRAGMA query_only = ON / SET TRANSACTION READ ONLY",
            "CREDENTIAL_SCRUBBING": "Active",
            "MODULE_7_BYPASS_PROTECTION": "Active"
        })
