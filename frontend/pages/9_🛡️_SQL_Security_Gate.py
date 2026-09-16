"""Module 7: Streamlit SQL Validator & Security Gate Sandbox.

Provides:
- Zero-Trust AST Security Gatekeeper
- Real-time Multi-point Security Checklist
- Numerical Risk Meter & Complexity Analyzer
- Cryptographic validation_id Token Generator (15-min TTL)
- Schema Hallucination & Cartesian Join Detector
- Validation Decision Audit History
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

import streamlit as st
import pandas as pd
from backend.database.connection import SessionLocal, init_db
from backend.database.connection_manager import connection_manager
from backend.database.models import User
from backend.database.models_validation import SQLValidationAuditLog
from sql_validator.schemas import SQLValidationRequest
from sql_validator.service import SQLValidatorService

st.set_page_config(
    page_title="SQL Security Gate - HR Analytics AI",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ SQL Validator & Security Gate")
st.caption("Module 7 — Zero-Trust AST Gatekeeper, Schema Allowlists, Risk Scoring, Cryptographic Token Issuance")

init_db()
db = SessionLocal()
service = SQLValidatorService(db=db)

# Tabs
tab_validator, tab_audit, tab_policies = st.tabs([
    "🔍 Interactive Validation Gate",
    "📜 Validation Decision Logs",
    "⚙️ Active Security Policies"
])

registered_dbs = connection_manager.list_databases_safe()
db_options = [d["database_id"] for d in registered_dbs] if registered_dbs else ["sqlite_hr_default"]

# ---------------- 1. INTERACTIVE VALIDATION GATE ----------------
with tab_validator:
    col_scope, col_user = st.columns([2, 2])
    with col_scope:
        selected_db = st.selectbox("Target Database Scope", db_options, index=0)
    with col_user:
        users = db.query(User).all()
        user_opts = {f"{u.username} ({u.role})": u for u in users} if users else {}
        selected_user_str = st.selectbox("Simulated Requesting User", list(user_opts.keys())) if user_opts else None
        sim_user = user_opts.get(selected_user_str) if selected_user_str else None

    # Pre-canned query templates for testing
    templates = {
        "Custom SQL": "",
        "✅ Safe Headcount Query": "SELECT d.name AS department, COUNT(e.id) AS total_headcount\nFROM employees e\nJOIN departments d ON e.department_id = d.id\nWHERE e.status = 'Active' AND e.is_current = 1\nGROUP BY d.name\nORDER BY total_headcount DESC;",
        "⚠️ High Risk: Missing WHERE on large table": "SELECT e.first_name, e.last_name, c.base_salary\nFROM employees e\nJOIN compensation_history c ON e.id = c.employee_id;",
        "🚫 Blocked: Malicious DDL Mutation (DROP TABLE)": "SELECT * FROM employees; DROP TABLE employees;",
        "🚫 Blocked: Destructive UPDATE Mutation": "UPDATE employees SET status = 'Terminated' WHERE id = 1;",
        "🚫 Blocked: Cartesian Cross Join": "SELECT e.first_name, d.name\nFROM employees e, departments d;",
        "🚫 Blocked: Schema Hallucination (Fake Table)": "SELECT * FROM non_existent_payroll_table WHERE balance > 1000;",
        "🚫 Blocked: Dangerous Function (xp_cmdshell)": "SELECT xp_cmdshell('dir') FROM employees;",
    }

    selected_tpl = st.selectbox("Load Test Scenario Template", list(templates.keys()))
    default_sql = templates[selected_tpl] if selected_tpl != "Custom SQL" else "SELECT e.first_name, e.last_name, d.name AS dept\nFROM employees e\nJOIN departments d ON e.department_id = d.id\nWHERE e.status = 'Active' AND e.is_current = 1\nLIMIT 50;"

    sql_input = st.text_area("SQL Statement to Validate", value=default_sql, height=160)

    col_btn, col_opt = st.columns([1, 2])
    with col_opt:
        allow_star = st.checkbox("Allow Wildcard Projections (SELECT *)", value=False)
    with col_btn:
        validate_clicked = st.button("🛡️ Validate SQL Safety", type="primary", width='stretch')

    if validate_clicked or "last_validation_result" in st.session_state:
        if validate_clicked:
            req = SQLValidationRequest(
                sql=sql_input,
                database_id=selected_db,
                user_id=sim_user.id if sim_user else None,
                username=sim_user.username if sim_user else "admin",
                user_role=sim_user.role if sim_user else "admin",
                department_id=sim_user.department_id if sim_user else None,
                allow_select_star=allow_star
            )
            result = service.validate_query(req)
            st.session_state["last_validation_result"] = result
        else:
            result = st.session_state["last_validation_result"]

        st.markdown("---")
        # Visual Status Header
        col_status, col_risk, col_token = st.columns([2, 2, 3])

        with col_status:
            if result.status == "APPROVED":
                st.success(f"### Status: {result.status} ✅")
                st.caption("Passed all zero-trust security checks. Execution token issued.")
            elif result.status == "REQUIRES_APPROVAL":
                st.warning(f"### Status: {result.status} ⚠️")
                st.caption("High complexity query requires elevated manager approval.")
            else:
                st.error(f"### Status: {result.status} ❌")
                st.caption("Security violation detected. Execution strictly prohibited.")

        with col_risk:
            st.metric(label="Risk Score (0 - 100)", value=f"{result.risk_score} / 100", delta=f"Level: {result.risk_level}", delta_color="inverse" if result.risk_score > 30 else "normal")

        with col_token:
            if result.validation_id:
                st.info(f"**Issued Validation ID:**\n`{result.validation_id}`\n\n**TTL Expires:** {result.expires_at}")
            else:
                st.markdown("**Validation Token:** `None (Unapproved)`")

        # Violations and Warnings
        if result.violations:
            st.error("#### 🚫 Fatal Violations (Execution Blockers)")
            for v in result.violations:
                st.markdown(f"- **{v}**")

        if result.warnings:
            st.warning("#### ⚠️ Security & Performance Warnings")
            for w in result.warnings:
                st.markdown(f"- {w}")

        # Checklist and Complexity split
        col_chk, col_cpx = st.columns([3, 2])

        with col_chk:
            st.markdown("#### 📋 Security & Compliance Checklist")
            chk_rows = []
            for item in result.checklist:
                chk_rows.append({
                    "Rule Check": item.check_name.replace("_", " ").title(),
                    "Result": "✅ PASSED" if item.passed else f"❌ {item.severity}",
                    "Details": item.details
                })
            st.dataframe(pd.DataFrame(chk_rows), width='stretch')

        with col_cpx:
            st.markdown("#### 📊 Structural Complexity Analysis")
            cm = result.complexity_metrics
            st.write(f"- **Referenced Tables:** {cm.table_count}")
            st.write(f"- **JOIN Operations:** {cm.join_count}")
            st.write(f"- **Subqueries:** {cm.subquery_count}")
            st.write(f"- **Aggregations:** {cm.aggregation_count}")
            st.write(f"- **GROUP BY:** {'Yes' if cm.has_group_by else 'No'}")
            st.write(f"- **ORDER BY:** {'Yes' if cm.has_order_by else 'No'}")
            st.write(f"- **Estimated Complexity:** {cm.estimated_complexity_score} / 100")

        # Technical Details Expander
        with st.expander("🔐 Cryptographic Integrity & Sanitized SQL"):
            st.code(result.sanitized_sql, language="sql")
            st.write(f"**SHA-256 Hash:** `{result.sql_hash}`")
            st.write(f"**Execution Permitted:** `{result.can_execute}`")

# ---------------- 2. VALIDATION AUDIT LOGS ----------------
with tab_audit:
    st.subheader("Historical Validation Decisions & Issued Tokens")
    logs = db.query(SQLValidationAuditLog).order_by(SQLValidationAuditLog.created_at.desc()).limit(50).all()
    if logs:
        log_rows = []
        for l in logs:
            log_rows.append({
                "Validation ID": l.validation_id,
                "Database": l.database_id,
                "User": l.username or "—",
                "Role": l.user_role or "—",
                "Status": l.status,
                "Risk Score": l.risk_score,
                "Risk Level": l.risk_level,
                "SQL Hash": l.sql_hash[:12] + "...",
                "Created At": str(l.created_at)
            })
        st.dataframe(pd.DataFrame(log_rows), width='stretch')
    else:
        st.info("No validation decisions logged yet.")

# ---------------- 3. ACTIVE POLICIES ----------------
with tab_policies:
    st.subheader("Zero-Trust Security Policies")
    st.write("Current enterprise guardrail parameters configured in `sql_validator/policy_engine.py`:")
    st.json({
        "Allow Wildcard (SELECT *)": False,
        "Max Permitted Joins": 5,
        "Disallow Cartesian Cross Joins": True,
        "Disallow Obfuscating Comments": True,
        "Require WHERE on Large Tables": True,
        "Token Expiration TTL": "15 minutes",
        "Safe Functions Whitelist": ["COUNT", "SUM", "AVG", "MIN", "MAX", "COALESCE", "ROUND", "DATE", "CAST", "CASE", "WHEN"],
        "Prohibited Functions": ["xp_cmdshell", "benchmark", "sleep", "pg_sleep", "load_file", "into outfile", "eval"]
    })

db.close()
