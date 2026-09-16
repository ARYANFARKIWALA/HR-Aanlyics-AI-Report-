"""Module 2: SQL Report Detail & Knowledge Viewer.

Displays:
- Comprehensive Report Header & Metadata
- Tables, Columns, Joins, Filters, Parameters, and Effective-Dating breakdown
- Syntax-highlighted Original SQL and Normalized SQL
- Version History with visual unified diff comparison
- Role-based Approval, Rejection, and Archive workflows
- LlamaIndex-ready RAG Knowledge Document preview
"""

import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(FRONTEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import streamlit as st

from backend.database.connection import SessionLocal
from backend.database.models import User
from backend.database.models_repo import SQLReport
from backend.services.sql_repository_service import SQLRepositoryService
from rag.sql_knowledge_builder import SQLKnowledgeBuilder

st.set_page_config(page_title="SQL Report Detail", page_icon="📄", layout="wide")

if "current_username" not in st.session_state:
    st.session_state.current_username = "admin"

db_session = SessionLocal()
current_user = db_session.query(User).filter(User.username == st.session_state.current_username).first()
if not current_user:
    current_user = db_session.query(User).first()

# Select report to view
reports_all = db_session.query(SQLReport).order_by(SQLReport.updated_at.desc()).all()
if not reports_all:
    st.warning("No SQL reports available in the repository. Please add or import a report first.")
    st.stop()

code_map = {r.report_code: r.id for r in reports_all}
report_options = [f"{r.report_code} - {r.report_name} [{r.category}]" for r in reports_all]

default_idx = 0
if "selected_report_id" in st.session_state:
    for idx, r in enumerate(reports_all):
        if r.id == st.session_state.selected_report_id:
            default_idx = idx
            break

selected_option = st.selectbox("Select SQL Report to Inspect:", report_options, index=default_idx)
selected_code = selected_option.split(" - ")[0]
selected_id = code_map[selected_code]

# Fetch full report
report = db_session.query(SQLReport).filter(SQLReport.id == selected_id).first()
meta = report.metadata_rel

# Viewer role check
if current_user.role == "viewer" and report.status != "APPROVED":
    st.error("⛔ Unauthorized: Viewer role cannot view unapproved SQL reports.")
    st.stop()

# Header Information
st.markdown(f"## 📄 {report.report_name}")
st.caption(f"**Code:** `{report.report_code}` | **Database:** `{report.database_id}` | **Category:** `{report.category}` | **Status:** `{report.status}` | **Version:** `v{report.version}`")

# Status Alert Box
if report.status == "APPROVED":
    st.success("✅ **APPROVED**: This report is certified and actively indexed as trusted knowledge for RAG and AI reporting.")
elif report.status == "PENDING_REVIEW":
    st.warning("⏳ **PENDING REVIEW**: Report imported and awaiting HR / Admin review.")
elif report.status == "INVALID":
    st.error(f"❌ **INVALID SYNTAX**: {report.validation_error}")
elif report.status == "ARCHIVED":
    st.info("📦 **ARCHIVED**: Excluded from active RAG knowledge retrieval.")
elif report.status == "REJECTED":
    st.error("🛑 **REJECTED**: Changes required before re-submitting for review.")

st.divider()

# Metadata Badges
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Complexity", meta.complexity_level if meta else "LOW", f"Score: {meta.complexity_score if meta else 1.0}")
m2.metric("Tables Joined", meta.table_count if meta else 0)
m3.metric("Effective Dating", "YES" if (meta and meta.uses_effective_dating) else "NO")
m4.metric("Security Filter", "YES" if (meta and meta.uses_security_filter) else "NO")
m5.metric("Date Logic", "YES" if (meta and meta.has_date_logic) else "NO")
m6.metric("Parameters", len(report.parameters))

# Tabs for SQL Code, Structural Breakdown, Version History, Approval, and RAG Knowledge
detail_tabs = st.tabs([
    "💻 SQL Query & AST",
    "📊 Schema & Join Breakdown",
    "🕒 Version History & Diffs",
    "⚖️ Approval & Governance",
    "🧠 RAG Knowledge Document"
])

# -------------------------------------------------------------
# Tab 1: SQL Code
# -------------------------------------------------------------
with detail_tabs[0]:
    st.markdown("#### Original Verified SQL Query (Preserved Intact):")
    st.code(report.sql_query, language="sql")

    with st.expander("Normalized Canonical SQL (Used for Duplicate Detection Hashing)"):
        st.code(report.normalized_sql, language="sql")
        st.caption(f"SQL SHA-256 Hash: `{report.sql_hash}`")

# -------------------------------------------------------------
# Tab 2: Schema & Join Breakdown
# -------------------------------------------------------------
with detail_tabs[1]:
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown("##### 🏢 Business Purpose & Description")
        st.write(f"**Description:** {report.description}")
        st.write(f"**Business Purpose:** {report.business_purpose or 'Not specified'}")

        if meta:
            st.markdown("##### 📋 Tables & Columns")
            tables = json.loads(meta.tables_json) if meta.tables_json else []
            columns = json.loads(meta.columns_json) if meta.columns_json else []
            st.write(f"**Tables:** {', '.join(tables)}")
            st.write(f"**Columns:** {', '.join(columns)}")

            if meta.aggregations_json:
                aggs = json.loads(meta.aggregations_json)
                agg_list = [f"{a.get('function')}({a.get('column')})" for a in aggs]
                st.write(f"**Aggregations:** {agg_list}")

    with col_d2:
        st.markdown("##### 🔗 Joins & Relationships")
        if meta and meta.joins_json:
            joins = json.loads(meta.joins_json)
            if joins:
                for j in joins:
                    st.info(f"**{j.get('join_type')}** `{j.get('right_table')}` ON `{j.get('join_condition')}`")
            else:
                st.write("Single table query (No joins).")

        st.markdown("##### 📅 Effective-Dating & Security")
        if meta and meta.uses_effective_dating:
            eff = json.loads(meta.effective_dating_details) if meta.effective_dating_details else []
            st.warning(f"**Effective Dating Applied:** {'; '.join(eff)}")
        if meta and meta.uses_security_filter:
            sec = json.loads(meta.security_filters_details) if meta.security_filters_details else []
            st.info(f"**Security Filter Columns:** {', '.join(sec)}")

        if report.parameters:
            st.markdown("##### 🎛️ Query Parameters")
            param_data = [
                {"Name": p.parameter_name, "Type": p.parameter_type, "Required": p.required}
                for p in report.parameters
            ]
            st.table(pd.DataFrame(param_data))

# -------------------------------------------------------------
# Tab 3: Version History & Diffs
# -------------------------------------------------------------
with detail_tabs[2]:
    st.markdown("#### 🕒 Version History")
    versions = report.versions
    st.write(f"Total Versions Recorded: **{len(versions)}**")

    ver_rows = [
        {
            "Version": f"v{v.version_number}",
            "Change Description": v.change_description,
            "Created At": v.created_at.strftime("%Y-%m-%d %H:%M") if v.created_at else ""
        }
        for v in versions
    ]
    st.table(pd.DataFrame(ver_rows))

    if len(versions) >= 2:
        st.divider()
        st.markdown("#### 🔄 Compare Versions (Unified Diff)")
        v_nums = [v.version_number for v in versions]
        c1, c2, c3 = st.columns([2, 2, 2])
        with c1:
            sel_v1 = st.selectbox("Base Version:", v_nums, index=len(v_nums) - 1)
        with c2:
            sel_v2 = st.selectbox("Comparison Version:", v_nums, index=0)

        diff_res = SQLRepositoryService.compare_versions(db_session, report.id, sel_v1, sel_v2)
        st.markdown(f"**Diff between v{sel_v1} and v{sel_v2}:**")
        st.code(diff_res["diff_text"], language="diff")

# -------------------------------------------------------------
# Tab 4: Approval & Governance
# -------------------------------------------------------------
with detail_tabs[3]:
    st.markdown("#### ⚖️ Governance & Review Decisions")

    # Display prior approvals/rejections
    if report.approvals:
        for a in report.approvals:
            st.caption(f"**{a.action}** at {a.created_at.strftime('%Y-%m-%d %H:%M')}: {a.comment}")
    else:
        st.caption("No approval decisions recorded yet.")

    # Action controls based on role
    if current_user.role in ["admin", "hr_manager"]:
        st.divider()
        st.markdown("#### Perform Governance Action:")
        action_choice = st.radio("Select Action:", ["Approve Report", "Reject Report", "Archive Report"], horizontal=True)

        if action_choice == "Approve Report":
            app_comment = st.text_input("Approval Comment:", value="Approved for enterprise RAG knowledge base.")
            if st.button("✅ Approve Report", type="primary"):
                try:
                    SQLRepositoryService.approve_report(db_session, report.id, current_user, comment=app_comment)
                    st.success("Report approved successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        elif action_choice == "Reject Report":
            rej_reason = st.text_input("Rejection Reason (Required):", placeholder="e.g. Missing effective-dating filter for historical transfers.")
            if st.button("🛑 Reject Report"):
                if not rej_reason.strip():
                    st.warning("Please provide a rejection reason.")
                else:
                    SQLRepositoryService.reject_report(db_session, report.id, current_user, reason=rej_reason)
                    st.success("Report rejected.")
                    st.rerun()

        elif action_choice == "Archive Report":
            arch_reason = st.text_input("Archive Reason:", value="Superseded or retired reporting logic.")
            if st.button("📦 Archive Report"):
                SQLRepositoryService.archive_report(db_session, report.id, current_user, reason=arch_reason)
                st.success("Report archived.")
                st.rerun()
    else:
        st.info("ℹ️ Only ADMIN and HR_ADMIN roles can approve, reject, or archive reports.")

# -------------------------------------------------------------
# Tab 5: RAG Knowledge Document
# -------------------------------------------------------------
with detail_tabs[4]:
    st.markdown("#### 🧠 LlamaIndex-Compatible RAG Knowledge Document")
    st.caption("This structured document is exported to Module 5 (RAG) when the report is in APPROVED status.")

    doc = SQLKnowledgeBuilder.build_knowledge_document(report, meta)

    st.markdown("##### 📄 Document Markdown Text:")
    st.text_area("RAG Document Content:", value=doc.text_content, height=280)

    st.markdown("##### 🏷️ Attached RAG Metadata (Permission-Aware):")
    st.json(doc.metadata)

db_session.close()
