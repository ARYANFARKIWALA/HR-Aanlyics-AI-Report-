"""Module 6: Streamlit AI Natural Language HR Report Builder.

Provides:
- Conversational / Prompt-based HR Report Creation
- Multi-Dialect SQL Generation (PostgreSQL, SQLite, MySQL, SQL Server, Oracle)
- Preserves Organizational Rules & Historical Report Knowledge
- Plain English Query Explanations for Business Users
- Applied Rules & Source Report Traceability
- Safety & Hallucination Guardrails
- Query Plan Inspection
"""

import os
import sys

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PAGES_DIR = CURRENT_DIR
FRONTEND_DIR = os.path.dirname(PAGES_DIR)
PROJECT_ROOT = os.path.dirname(FRONTEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import streamlit as st

from backend.database.connection import SessionLocal, init_db
from backend.database.connection_manager import connection_manager
from text_to_sql.schemas import TextToSQLRequest
from text_to_sql.service import TextToSQLService

st.set_page_config(
    page_title="AI Report Builder - HR Analytics AI",
    page_icon="💬",
    layout="wide"
)

st.title("💬 AI Text-to-SQL HR Report Builder")
st.caption("Module 6 — Natural Language to Safe, Dialect-Specific, Rule-Preserved SQL Queries")

init_db()
db = SessionLocal()
service = TextToSQLService(db)

# Sidebar Configurations & User Context
st.sidebar.header("🎯 Context & Target Settings")

registered_dbs = connection_manager.list_databases_safe()
db_options = [d["database_id"] for d in registered_dbs] if registered_dbs else ["sqlite_hr_default"]
selected_db_id = st.sidebar.selectbox("Target HR Database", db_options, index=0)

dialects = ["sqlite", "postgresql", "mysql", "sqlserver", "oracle"]
target_dialect = st.sidebar.selectbox("Target SQL Dialect", dialects, index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("👤 User Security Context")
user_role = st.sidebar.selectbox("Simulated User Role", ["admin", "hr_manager", "department_head", "employee"], index=0)
user_dept = st.sidebar.text_input("Department Context", value="Engineering" if user_role != "admin" else "")

as_of_date = st.sidebar.text_input("As-of Date (Temporal Context)", value="current")

# Main Interface: Reporting Query Prompt
st.subheader("What HR Report would you like to build?")

# Preset sample questions
col_p1, col_p2, col_p3, col_p4 = st.columns(4)
sample_query = None
if col_p1.button("👥 Headcount by Dept"):
    sample_query = "Show active headcount by department"
if col_p2.button("💰 Avg Salary by Dept"):
    sample_query = "What is the average salary by department?"
if col_p3.button("📉 Turnover & Attrition"):
    sample_query = "Show employee turnover rate by department"
if col_p4.button("⭐ Top 10 Earners"):
    sample_query = "Show top 10 highest paid employees with department"

query_input = st.text_area(
    "Enter your reporting question in plain English:",
    value=sample_query if sample_query else "Show active headcount and average salary by department",
    height=90
)

col_gen, col_clear = st.columns([2, 10])
with col_gen:
    generate_btn = st.button("🚀 Generate SQL", type="primary", width='stretch')

if generate_btn and query_input:
    req = TextToSQLRequest(
        query=query_input,
        database_id=selected_db_id,
        user_role=user_role,
        user_department=user_dept if user_dept else None,
        date_context=as_of_date if as_of_date != "current" else None,
        include_explanation=True,
        include_plan=True
    )

    with st.spinner("Analyzing organizational knowledge, applying rules, and synthesizing SQL..."):
        resp = service.generate_sql(req)

    # Display Status
    if resp.status == "SUCCESS":
        st.success(f"✅ Generated Dialect-Aware SQL (Target Engine: `{resp.dialect.upper()}` | Confidence: {int(resp.confidence_score * 100)}%)")

        col_sql, col_meta = st.columns([7, 5])

        with col_sql:
            st.markdown("### 📝 Generated SQL Statement")
            st.code(resp.sql, language="sql")

            c_act1, c_act2 = st.columns(2)
            with c_act1:
                st.button("📋 Validate in Module 7", key="btn_m7", help="Passes query to Module 7 SQL Validator & Security Guard")
            with c_act2:
                st.info("ℹ️ Execution strictly deferred to Module 8.")

        with col_meta:
            st.markdown("### 🔍 Query Summary")
            st.markdown(f"- **Entities Used:** `{', '.join(resp.tables_used)}`")
            st.markdown(f"- **Columns Selected:** `{', '.join(resp.columns_used[:10])}`")
            st.markdown(f"- **Target Dialect:** `{resp.dialect}`")
            st.markdown("- **Read-Only Invariant:** Verified")

        # Tabs for Explanation, Applied Rules, and Query Plan
        tab_exp, tab_rules, tab_plan = st.tabs([
            "📖 Plain-English Explanation",
            "⚖️ Applied Rules & Provenance",
            "📐 Query Plan (AST)"
        ])

        with tab_exp:
            if resp.explanation:
                st.markdown(resp.explanation)
            else:
                st.info("No explanation generated.")

        with tab_rules:
            if resp.applied_rules:
                st.markdown("#### Approved Organizational Rules Enforced in Query:")
                for r in resp.applied_rules:
                    st.markdown(f"- **[{r.get('rule_code')}]** {r.get('rule_name')}: `{r.get('rule_expression')}`")
            else:
                st.info("No specific business rules were required for this query.")

            if resp.reused_reports:
                st.markdown("#### Reused Enterprise SQL Report Templates:")
                for rp in resp.reused_reports:
                    st.markdown(f"- **[{rp.get('report_code')}]** {rp.get('report_name')} ({rp.get('category')})")

        with tab_plan:
            if resp.query_plan:
                st.json(resp.query_plan)
            else:
                st.info("Query plan not available.")

    elif resp.status == "AMBIGUOUS_QUERY":
        st.warning("⚠️ **Ambiguous Query Detected**")
        st.markdown(resp.message or "Please clarify your request:")
        if resp.clarification:
            for q in resp.clarification.questions:
                st.markdown(f"- **{q}**")
            st.markdown("#### Suggested Alternative Prompts:")
            for s in resp.clarification.suggested_queries:
                st.code(s, language="markdown")

    elif resp.status == "INSUFFICIENT_CONTEXT":
        st.error(f"❌ **Insufficient Knowledge Base Context:** {resp.message}")
        st.info("💡 Tip: Try asking questions related to approved HR tables (employees, departments, salaries) or import verified SQL reports into Module 2.")

    elif resp.status == "BLOCKED_BY_SAFETY":
        st.error(f"🛡️ **Blocked by SQL Safety Guardrails:** {resp.message}")
        if resp.sql:
            st.code(resp.sql, language="sql")

st.markdown("---")
st.subheader("📜 Recent Query Generations")
history = TextToSQLService.get_history()
if history:
    df_hist = pd.DataFrame(history)
    st.dataframe(df_hist[["query", "status", "dialect", "confidence_score", "sql"]], width='stretch')
else:
    st.caption("No queries generated in this session yet.")
