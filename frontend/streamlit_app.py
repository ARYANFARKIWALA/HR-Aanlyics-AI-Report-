"""HR Analytics AI Report Builder - Streamlit Enterprise Dashboard.

Empowers HR business users and executives to query HR data in natural language,
transform existing SQL knowledge into intelligent reports, view interactive Plotly dashboards,
and export boardroom-ready PDF and Excel reports.
"""

import os
import sys

# Ensure project root is in Python sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from analytics.metrics import HRMetricsCalculator
from analytics.visualization import HRVisualizer

# Import Core Domain Modules
from backend.database.connection import SessionLocal, init_db
from backend.database.connection_manager import connection_manager
from backend.database.models import SQLRepository, User
from backend.database.seeder import seed_database
from backend.services.query_service import QueryService
from backend.services.report_service import ReportService
from rag.retrieval import rag_retriever
from sql.parser import SQLParser

# Page Setup
st.set_page_config(
    page_title="HR Analytics AI Report Builder",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 26px;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 2px;
    }
    .sub-header {
        font-size: 14px;
        color: #64748B;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #1E3A8A;
    }
    .metric-label {
        font-size: 12px;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .pipeline-badge {
        display: inline-block;
        background-color: #EEF2FF;
        color: #4F46E5;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def setup_application():
    """Initializes schema, seeds database, and builds RAG vector indices."""
    init_db()
    seed_database()
    session = SessionLocal()
    try:
        rag_retriever.initialize(session)
    finally:
        session.close()
    return True


setup_application()


# -------------------------------------------------------------
# Sidebar: User Role & Database Target
# -------------------------------------------------------------
st.sidebar.markdown("### 🏢 HR Analytics AI Assistant")
st.sidebar.markdown("**Enterprise Reporting Platform**")
st.sidebar.divider()

# Session State for User Authentication / Persona
if "current_username" not in st.session_state:
    st.session_state.current_username = "admin"

user_role_options = {
    "admin": "System Administrator (Full Access)",
    "hr_manager": "HR Director (David Patel - Operations)",
    "hr_analyst": "People Analyst (Priya Sharma - PII Masked)",
    "executive": "Executive / CPO (Victoria Sterling - Boardroom)",
}

selected_username = st.sidebar.selectbox(
    "Active User Persona (RBAC):",
    options=list(user_role_options.keys()),
    format_func=lambda x: user_role_options[x],
    index=list(user_role_options.keys()).index(st.session_state.current_username)
)
st.session_state.current_username = selected_username

# Fetch User object
db_session: Session = SessionLocal()
current_user = db_session.query(User).filter(User.username == selected_username).first()
if not current_user:
    current_user = db_session.query(User).first()

st.sidebar.caption(f"Role: **{current_user.role.upper()}** | Dept ID: **{current_user.department_id or 'All'}**")

st.sidebar.divider()

# Module 1: Database Target Selector
st.sidebar.markdown("#### 🗄️ Module 1: Target Database")
registered_dbs = connection_manager.list_databases_safe()
db_options = [d["database_id"] for d in registered_dbs]
selected_db_id = st.sidebar.selectbox("Connected Database Target:", db_options, index=0)

current_schema = connection_manager.get_schema(selected_db_id)
dialect_rules = connection_manager.get_dialect_rules(selected_db_id)

st.sidebar.caption(f"Dialect: **{dialect_rules.dialect_name.upper()}** | Tables: **{len(current_schema.tables)}**")
st.sidebar.caption(f"Schema Hash: `{current_schema.schema_hash[:10]}...`")
st.sidebar.page_link("pages/5_🔍_Schema_Explorer.py", label="Schema & Metadata Explorer (M3)", icon="🔍")
st.sidebar.page_link("pages/1_📚_SQL_Repository.py", label="SQL Knowledge Repository (M2)", icon="📚")

st.sidebar.divider()

st.sidebar.markdown("#### 💡 Quick Prompts")
quick_prompts = [
    "Show employee attrition by department in 2026",
    "Active Headcount by Department & Cost Center",
    "High Performer Retention and Flight Risk Analysis",
    "Compensation Equity & Compa-Ratio Distribution",
    "Gender Diversity & Representation Across Departments",
    "Average Employee Tenure & Turnover by Work Location",
    "Leave Utilization and Absence Impact by Department"
]

for p in quick_prompts:
    if st.sidebar.button(p, key=f"quick_{p}", width='stretch'):
        st.session_state.active_prompt = p

if "active_prompt" not in st.session_state:
    st.session_state.active_prompt = "Show employee attrition by department in 2026"


# -------------------------------------------------------------
# Main Application Tabs
# -------------------------------------------------------------
tabs = st.tabs([
    "🤖 AI Query Assistant",
    "📚 Enterprise SQL Catalog",
    "📊 HR Analytics Dashboard",
    "📑 Report Builder & Export",
    "🔌 Database & Schema (Module 1)",
    "🛡️ Security & Audit Trail"
])


# =============================================================
# Tab 1: AI Query Assistant
# =============================================================
with tabs[0]:
    st.markdown('<div class="main-header">AI Natural Language Reporting Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Transforming enterprise HR questions into verified, dialect-aware SQL with AST validation and plain-English explanations.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([5, 1])
    with col1:
        query_input = st.text_input(
            "Ask a business question in plain English:",
            value=st.session_state.active_prompt,
            placeholder="e.g. What is the voluntary turnover rate across engineering teams?"
        )
    with col2:
        st.write("")
        st.write("")
        run_query_btn = st.button("Generate Report", type="primary", width='stretch')

    if run_query_btn or ("last_result" in st.session_state and st.session_state.get("last_query") == query_input):
        with st.spinner("Processing natural language query through AI pipeline..."):
            result = QueryService.process_natural_query(
                natural_query=query_input,
                user=current_user,
                session=db_session
            )
            st.session_state.last_result = result
            st.session_state.last_query = query_input

    if "last_result" in st.session_state:
        res = st.session_state.last_result

        # Display Pipeline Execution Badges
        st.markdown(
            '<div style="margin: 12px 0;">'
            '<span class="pipeline-badge">1. Query Understanding</span>'
            '<span class="pipeline-badge">2. RAG Knowledge Matching</span>'
            '<span class="pipeline-badge">3. LLM Generation</span>'
            '<span class="pipeline-badge">4. SQLGlot AST Validation</span>'
            '<span class="pipeline-badge">5. Row-Level Security</span>'
            '<span class="pipeline-badge">6. Safe Execution</span>'
            '</div>',
            unsafe_allow_html=True
        )

        if not res["success"]:
            st.error(f"❌ {res.get('error', 'Execution error occurred')}")
        else:
            # Metadata bar
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Rows Returned", res.get("row_count", 0))
            c2.metric("Execution Latency", f"{res.get('execution_time_ms', 0)} ms")
            c3.metric("Matched Template", res.get("matched_template") or "Custom SQL Synthesis")
            c4.metric("Security Guardrails", "PASSED (Read-Only)")

            st.divider()

            # Data and Chart Columns
            data_col, chart_col = st.columns([6, 5])
            with data_col:
                st.markdown("#### 📋 Tabular Report Data")
                df_res = pd.DataFrame(res["data"])
                if not df_res.empty:
                    st.dataframe(df_res, width='stretch', height=360)
                else:
                    st.info("Query succeeded with 0 rows returned matching the criteria.")

            with chart_col:
                st.markdown("#### 📈 Interactive Visualization")
                if not df_res.empty:
                    auto_fig = HRVisualizer.create_auto_chart(df_res, title=query_input)
                    if auto_fig:
                        st.plotly_chart(auto_fig, width='stretch')
                    else:
                        st.info("Chart view is optimized for tabular queries containing at least one category and one metric.")
                else:
                    st.info("No data available to plot.")

            # Plain English SQL Explanation & AST Analysis
            with st.expander("🔍 Plain-English SQL Explanation & Business Logic (For Business Users)", expanded=True):
                st.markdown(res.get("explanation", "No explanation generated."))
                st.markdown("##### Executed SQL Query (Preserving Enterprise Business Rules & Effective Dating):")
                st.code(res.get("sql", ""), language="sql")

            # One-click export shortcuts
            st.markdown("#### 🚀 Export This Analysis")
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                if st.button("Generate Boardroom PDF Report", key="pdf_btn_tab1", width='stretch'):
                    rpt_payload = ReportService.generate_report_payload(
                        session=db_session,
                        title=query_input,
                        category="Workforce Analytics",
                        sql_query=res["sql"],
                        data_columns=res["columns"],
                        data_rows=res["data"],
                        user=current_user
                    )
                    pdf_bytes = ReportService.export_pdf(rpt_payload)
                    st.download_button(
                        label="⬇️ Download Boardroom PDF",
                        data=pdf_bytes,
                        file_name=f"{rpt_payload.report_id}.pdf",
                        mime="application/pdf",
                        width='stretch'
                    )
            with col_exp2:
                if st.button("Generate Multi-Tab Excel Workbook", key="excel_btn_tab1", width='stretch'):
                    rpt_payload = ReportService.generate_report_payload(
                        session=db_session,
                        title=query_input,
                        category="Workforce Analytics",
                        sql_query=res["sql"],
                        data_columns=res["columns"],
                        data_rows=res["data"],
                        user=current_user
                    )
                    excel_bytes = ReportService.export_excel(rpt_payload)
                    st.download_button(
                        label="⬇️ Download Formatted Excel (.xlsx)",
                        data=excel_bytes,
                        file_name=f"{rpt_payload.report_id}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width='stretch'
                    )


# =============================================================
# Tab 2: Enterprise SQL Catalog
# =============================================================
with tabs[1]:
    st.markdown('<div class="main-header">Enterprise SQL Knowledge Repository</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Catalog of verified historical enterprise HR SQL reports containing effective-dating logic, multi-table joins, and business rules.</div>', unsafe_allow_html=True)

    categories = ["All", "Headcount", "Attrition", "Compensation", "Performance", "Diversity", "Compliance"]
    sel_cat = st.selectbox("Filter by Category:", categories)

    q = db_session.query(SQLRepository)
    if sel_cat != "All":
        q = q.filter(SQLRepository.category == sel_cat)
    templates = q.order_by(SQLRepository.report_title).all()

    st.write(f"Showing **{len(templates)}** verified enterprise SQL templates:")

    for t in templates:
        with st.expander(f"📄 **{t.report_title}** [{t.category.upper()}]", expanded=False):
            st.markdown(f"**Description:** {t.business_description}")
            st.markdown(f"**Business Rules:** {t.business_rules_explained}")
            st.markdown(f"**Joins Logic:** {t.joins_explained}")
            st.markdown(f"**Effective-Dating Logic:** {t.effective_dating_explained}")
            st.markdown(f"**Tags:** `{t.tags}` | **Author:** {t.author}")

            st.code(t.raw_sql, language="sql")

            col_btn1, col_btn2 = st.columns([2, 4])
            with col_btn1:
                if st.button("▶️ Run This Report", key=f"run_tmpl_{t.id}"):
                    st.session_state.active_prompt = t.report_title
                    st.rerun()
            with col_btn2:
                target_dialect = st.selectbox(
                    "Transpile Dialect (SQLGlot):",
                    ["postgres", "mysql", "tsql", "oracle", "sqlite"],
                    key=f"trans_{t.id}"
                )
                transpiled = SQLParser.transpile_query(t.raw_sql, from_dialect="sqlite", to_dialect=target_dialect)
                if st.button("Show Transpiled SQL", key=f"btn_trans_{t.id}"):
                    st.code(transpiled, language="sql")


# =============================================================
# Tab 3: HR Analytics Dashboard
# =============================================================
with tabs[2]:
    st.markdown('<div class="main-header">Executive HR Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Live workforce metrics, retention benchmarks, compensation parity, and organizational health.</div>', unsafe_allow_html=True)

    kpis = HRMetricsCalculator.get_executive_summary_kpis(db_session)

    # 6 Top KPI Cards
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Active Headcount", f"{kpis['active_headcount']:,}", f"Total: {kpis['total_headcount']}")
    m2.metric("Turnover Rate", f"{kpis['attrition_rate_pct']}%", f"Voluntary: {kpis['voluntary_attrition_rate_pct']}%", delta_color="inverse")
    m3.metric("Avg Base Salary", f"${kpis['avg_base_salary']:,.0f}")
    m4.metric("Compa-Ratio", f"{kpis['avg_compa_ratio']:.2f}", "Midpoint = 1.00")
    m5.metric("Female Ratio", f"{kpis['female_representation_pct']}%", "DEI Benchmark")
    m6.metric("Avg Performance", f"{kpis['avg_performance_rating']:.2f} / 5.0")

    st.divider()

    # Visual Charts
    dash_col1, dash_col2 = st.columns(2)
    with dash_col1:
        st.plotly_chart(HRVisualizer.create_headcount_donut(kpis["department_breakdown"]), width='stretch')

    with dash_col2:
        attrition_data = HRMetricsCalculator.get_attrition_by_department(db_session)
        st.plotly_chart(HRVisualizer.create_attrition_bar(attrition_data), width='stretch')


# =============================================================
# Tab 4: Report Builder & Export Center
# =============================================================
with tabs[3]:
    st.markdown('<div class="main-header">Boardroom HR Report Builder</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Compile executive narratives, KPI tables, and structured query findings into corporate PDF and Excel reports.</div>', unsafe_allow_html=True)

    report_templates = db_session.query(SQLRepository).all()
    template_titles = [t.report_title for t in report_templates]
    chosen_title = st.selectbox("Select Report Topic to Generate:", template_titles)
    chosen_record = next(t for t in report_templates if t.report_title == chosen_title)

    if st.button("Synthesize Executive Report Briefing", type="primary"):
        with st.spinner("Executing query and generating AI executive briefing..."):
            from sql.executor import SQLExecutor
            exec_res = SQLExecutor.execute(db_session, chosen_record.raw_sql)
            
            report_data = ReportService.generate_report_payload(
                session=db_session,
                title=chosen_record.report_title,
                category=chosen_record.category,
                sql_query=chosen_record.raw_sql,
                data_columns=exec_res.columns,
                data_rows=exec_res.data,
                user=current_user,
                business_rules=chosen_record.business_rules_explained,
                effective_dating_notes=chosen_record.effective_dating_explained
            )
            st.session_state.active_report_data = report_data

    if "active_report_data" in st.session_state:
        rpt: ReportService = st.session_state.active_report_data

        st.success(f"Report '{rpt.title}' synthesized successfully! Report ID: {rpt.report_id}")
        st.markdown("### AI Executive Strategic Briefing:")
        st.markdown(rpt.executive_summary)

        st.markdown("### Report Downloads:")
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            pdf_bytes = ReportService.export_pdf(rpt)
            st.download_button(
                "⬇️ Download Boardroom PDF Report",
                data=pdf_bytes,
                file_name=f"{rpt.report_id}.pdf",
                mime="application/pdf",
                width='stretch'
            )
        with d_col2:
            excel_bytes = ReportService.export_excel(rpt)
            st.download_button(
                "⬇️ Download Multi-Tab Excel Workbook (.xlsx)",
                data=excel_bytes,
                file_name=f"{rpt.report_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='stretch'
            )


# =============================================================
# Tab 5: Module 1: Database Connections & Schema
# =============================================================
with tabs[4]:
    st.markdown('<div class="main-header">Module 1: Database Connection & Schema Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Multi-database connectors, dialect-awareness, schema discovery, credentials/knowledge split, and allowlist truth.</div>', unsafe_allow_html=True)

    st.markdown("#### Registered Databases:")
    dbs_info = connection_manager.list_databases_safe()
    st.table(pd.DataFrame(dbs_info)[["database_id", "display_name", "db_type", "table_count", "schema_hash"]])

    st.divider()

    # Schema Viewer
    st.markdown("#### 🔎 Discovered Schema Structure (Allowlist Source of Truth):")
    schema_view_id = st.selectbox("Inspect Schema for Database:", [d["database_id"] for d in dbs_info])
    selected_schema = connection_manager.get_schema(schema_view_id)

    st.caption(f"**Schema Hash:** `{selected_schema.schema_hash}` | **Discovered At:** {selected_schema.discovered_at}")

    table_choices = [t["table_name"] for t in selected_schema.tables]
    chosen_tbl_name = st.selectbox("Select Table to Inspect:", table_choices)
    chosen_table = next(t for t in selected_schema.tables if t["table_name"] == chosen_tbl_name)

    st.write(f"Table: **{chosen_tbl_name}** | Approximate Rows: **{chosen_table['row_count']}**")
    st.dataframe(pd.DataFrame(chosen_table["columns"]), width='stretch')

    if chosen_table.get("foreign_keys"):
        st.markdown("**Foreign Key Relationships:**")
        st.json(chosen_table["foreign_keys"])

    st.divider()

    # Test Connection
    st.markdown("#### 🧪 Test New Database Connection (Component 1):")
    t_c1, t_c2 = st.columns([2, 5])
    with t_c1:
        test_db_type = st.selectbox("Target Database Type:", ["postgresql", "mysql", "sqlserver", "oracle", "sqlite"])
    with t_c2:
        test_db_url = st.text_input("Connection String / URL:", placeholder="postgresql://user:password@localhost:5432/hr_dw")

    if st.button("Test Reachability & Authentication"):
        if not test_db_url:
            st.warning("Please enter a connection URL.")
        else:
            success, msg, diag = connection_manager.test_connection(test_db_type, test_db_url)
            if success:
                st.success(f"✅ {msg}")
                st.json(diag)
            else:
                st.error(f"❌ {msg}")


# =============================================================
# Tab 6: Security & Audit Trail
# =============================================================
with tabs[5]:
    st.markdown('<div class="main-header">Security, RBAC & Query Audit Trail</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Immutable query logs, latency metrics, PII masking verification, and compliance oversight.</div>', unsafe_allow_html=True)

    from security.audit import AuditLogger
    logs = AuditLogger.get_recent_logs(db_session, limit=50)

    if logs:
        df_logs = pd.DataFrame(logs)
        st.dataframe(
            df_logs[["id", "timestamp", "username", "user_role", "status", "execution_time_ms", "row_count", "natural_query", "generated_sql"]],
            width='stretch'
        )
    else:
        st.info("No audit logs recorded yet.")

db_session.close()
