"""Module 8: Streamlit Query Execution Screen.

Provides:
- Cryptographic Handshake Execution (validation_id token lookup)
- High-Performance Execution Telemetry (duration ms, row caps, cache status)
- Exact-Type Interactive Results Table with Pagination & CSV Export
- Execution Audit Trail Inspector
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
from backend.database.models import User
from backend.database.models_validation import SQLValidationAuditLog
from backend.database.models_execution import QueryExecutionAuditLog
from query_execution.schemas import ExecuteQueryRequest
from query_execution.service import QueryExecutionService, QueryExecutionError

st.set_page_config(
    page_title="Query Execution - HR Analytics AI",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Query Execution Engine")
st.caption("Module 8 — Zero-Trust Handshake, Read-Only Pool, Exact Type Fidelity, Results Caching & Auditing")

init_db()
db = SessionLocal()
service = QueryExecutionService(db=db)

tab_exec, tab_history = st.tabs(["🚀 Execute Validated Query", "📜 Execution History"])

# ----------------- 1. EXECUTE QUERY TAB -----------------
with tab_exec:
    # 1. Fetch recent approved tokens to assist user
    approved_tokens = db.query(SQLValidationAuditLog).filter(
        SQLValidationAuditLog.status == "APPROVED"
    ).order_by(SQLValidationAuditLog.created_at.desc()).limit(10).all()

    token_options = {
        f"{t.validation_id} — {t.sanitized_sql[:60]}...": t.validation_id
        for t in approved_tokens
    }

    col_t_sel, col_t_man = st.columns([3, 2])
    with col_t_sel:
        if token_options:
            selected_token_label = st.selectbox("Select Recent Approved Token", list(token_options.keys()))
            selected_val_id = token_options[selected_token_label]
        else:
            st.info("No approved validation tokens available. Validate a query in Module 7 first.")
            selected_val_id = ""

    with col_t_man:
        manual_val_id = st.text_input("Or Enter Custom Validation Token (validation_id)", value=selected_val_id)

    active_val_id = manual_val_id.strip() if manual_val_id else selected_val_id

    # Display preview of approved query if token exists
    if active_val_id:
        val_entry = db.query(SQLValidationAuditLog).filter(
            SQLValidationAuditLog.validation_id == active_val_id
        ).first()
        if val_entry:
            with st.expander("👁️ Inspect Approved Query & Cryptographic Hash", expanded=False):
                st.code(val_entry.sanitized_sql, language="sql")
                st.write(f"- **Target Database:** `{val_entry.database_id}`")
                st.write(f"- **Status:** `{val_entry.status}`")
                st.write(f"- **SHA-256 Hash:** `{val_entry.sql_hash}`")
                st.write(f"- **Expires At:** `{val_entry.expires_at}`")

    col_btn, col_opt = st.columns([1, 2])
    with col_opt:
        bypass_cache = st.checkbox("Bypass Query Cache (Force Fresh Execution)", value=False)
    with col_btn:
        run_clicked = st.button("⚡ Execute Query", type="primary", width='stretch')

    if run_clicked:
        if not active_val_id:
            st.error("Please specify a valid validation_id token.")
        else:
            with st.spinner("Executing approved query against database..."):
                try:
                    admin_user = db.query(User).filter(User.username == "admin").first()
                    req = ExecuteQueryRequest(
                        validation_id=active_val_id,
                        bypass_cache=bypass_cache,
                        page=1,
                        page_size=500
                    )
                    res = service.execute(req, user=admin_user)

                    st.markdown("---")
                    # KPIs
                    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                    kpi1.metric("Status", res.status)
                    kpi2.metric("Execution Time", f"{res.execution_time_ms} ms")
                    kpi3.metric("Rows Returned", f"{res.total_rows:,}")
                    kpi4.metric("Cached Result", "⚡ Yes" if res.cached else "Fresh Query")

                    # Result DataFrame
                    if res.rows:
                        df_res = pd.DataFrame(res.rows)
                        st.subheader(f"Query Results ({len(df_res)} rows displayed)")
                        st.dataframe(df_res, width='stretch')

                        # CSV Download button
                        csv_data = df_res.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="📥 Download Results as CSV",
                            data=csv_data,
                            file_name=f"query_result_{res.execution_id}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("Query executed successfully, returning 0 rows.")

                except QueryExecutionError as qe:
                    st.error(f"❌ Handshake / Execution Violation: {str(qe)}")
                except Exception as ex:
                    st.error(f"❌ Execution Exception: {str(ex)}")

# ----------------- 2. EXECUTION HISTORY TAB -----------------
with tab_history:
    st.subheader("Historical Query Execution Logs")
    logs = db.query(QueryExecutionAuditLog).order_by(
        QueryExecutionAuditLog.created_at.desc()
    ).limit(50).all()

    if logs:
        rows = []
        for l in logs:
            rows.append({
                "Execution ID": l.execution_id,
                "Validation Token": l.validation_id or "—",
                "Database": l.database_id,
                "Status": l.status,
                "Rows": l.row_count,
                "Time (ms)": l.execution_time_ms,
                "Cached": "Yes" if l.cached else "No",
                "User": l.username or "—",
                "Executed At": str(l.created_at),
                "Error": l.error_message or "—"
            })
        st.dataframe(pd.DataFrame(rows), width='stretch')
    else:
        st.info("No query executions recorded yet.")

db.close()
