"""Module 2: Add SQL Report Interface.

Supports:
- Method 1: Manual SQL editor with real-time SQLGlot syntax validation
- Method 2: SQL file upload (.sql, .txt) with header metadata extraction
- Duplicate detection alerts
- Association with Module 1 selected database
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(FRONTEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from backend.database.connection import SessionLocal
from backend.database.models import User
from backend.database.connection_manager import connection_manager
from backend.services.sql_repository_service import SQLRepositoryService
from sql.parser import SQLParser
from sql.file_parser import SQLFileParser

st.set_page_config(page_title="Add SQL Report", page_icon="➕", layout="wide")

if "current_username" not in st.session_state:
    st.session_state.current_username = "admin"

db_session = SessionLocal()
current_user = db_session.query(User).filter(User.username == st.session_state.current_username).first()
if not current_user:
    current_user = db_session.query(User).first()

# Role permission check: Viewer and Analyst cannot add
if current_user.role not in ["admin", "hr_manager"]:
    st.error("⛔ Unauthorized: Only ADMIN and HR_ADMIN roles can import or add SQL reports.")
    st.stop()

st.markdown("## ➕ Add Existing HR SQL Report")
st.markdown("*Import existing reporting logic, joins, and effective-dating queries into the knowledge repository.*")
st.divider()

# Input Method Selection
input_method = st.radio("Select Ingestion Method:", ["Method 1: Manual SQL Editor", "Method 2: Single SQL File Upload (.sql, .txt)"], horizontal=True)

# Database Selector (from Module 1)
dbs = connection_manager.list_databases_safe()
db_options = [d["database_id"] for d in dbs]
selected_db_id = st.selectbox("Select Target HR Database (Module 1):", db_options, index=0)

dialect_rules = connection_manager.get_dialect_rules(selected_db_id)
st.caption(f"Target Database Dialect: **{dialect_rules.dialect_name.upper()}**")

st.write("")

# Form variables
report_name_val = ""
description_val = ""
purpose_val = ""
category_val = "Headcount"
tags_val = ""
sql_query_val = ""

if input_method == "Method 2: Single SQL File Upload (.sql, .txt)":
    uploaded_file = st.file_uploader("Upload .sql or .txt file:", type=["sql", "txt"])
    if uploaded_file:
        file_bytes = uploaded_file.read()
        file_text = file_bytes.decode("utf-8", errors="replace")
        parsed_entries = SQLFileParser.parse_content(file_text, filename=uploaded_file.name)
        if parsed_entries:
            first_entry = parsed_entries[0]
            report_name_val = first_entry.extracted_name or uploaded_file.name
            description_val = first_entry.extracted_description or ""
            purpose_val = first_entry.extracted_description or ""
            category_val = first_entry.extracted_category if first_entry.extracted_category != "Other" else "Headcount"
            tags_val = ", ".join(first_entry.extracted_tags)
            sql_query_val = first_entry.raw_sql
            st.success(f"Extracted query from **{uploaded_file.name}**")

# Report Metadata Fields
col_f1, col_f2 = st.columns(2)
with col_f1:
    rep_name = st.text_input("Report Name:", value=report_name_val, placeholder="e.g. Department Headcount by Cost Center")
    rep_category = st.selectbox(
        "Report Category:",
        ["Headcount", "Attrition", "Recruitment", "Attendance", "Leave", "Salary", "Compensation", "Performance", "Employee Demographics", "Department", "Job Role", "Location", "Tenure", "Other"],
        index=0
    )
    rep_tags = st.text_input("Tags (comma-separated):", value=tags_val, placeholder="e.g. headcount, department, payroll, budget")

with col_f2:
    rep_desc = st.text_area("Report Description:", value=description_val, placeholder="e.g. Shows active headcount broken down by department and cost center.", height=70)
    rep_purpose = st.text_area("Business Purpose (Context for AI/RAG):", value=purpose_val, placeholder="e.g. Used by HR leadership and finance for monthly workforce budget allocation.", height=70)

# SQL Query Editor
st.markdown("#### SQL Query Text (Preserved Exactly):")
default_sql = sql_query_val or """SELECT 
    d.name AS department_name,
    COUNT(e.id) AS employee_count
FROM departments d
JOIN employees e ON d.id = e.department_id
WHERE e.status = 'Active' AND e.is_current = 1
GROUP BY d.name;"""

sql_text_input = st.text_area("Enter SQL Statement:", value=default_sql, height=180)

# Real-time Validation Preview
if sql_text_input.strip():
    with st.expander("🔍 Live Syntax & Metadata Analysis (Non-Executing)", expanded=False):
        parsed = SQLParser.parse_query(sql_text_input, read_dialect=dialect_rules.dialect_name)
        if parsed.is_valid:
            st.success("✅ Syntax Valid (Parsed via SQLGlot)")
            m1, m2, m3, m4 = st.columns(4)
            m1.write(f"**Tables:** {', '.join(parsed.tables)}")
            m2.write(f"**Effective Dating:** {'YES' if parsed.uses_effective_dating else 'NO'}")
            m3.write(f"**Security Filter:** {'YES' if parsed.uses_security_filter else 'NO'}")
            m4.write(f"**Complexity:** {parsed.complexity_level} ({parsed.complexity_score})")
            if parsed.parameters:
                st.write(f"**Detected Parameters:** {[p['parameter_name'] for p in parsed.parameters]}")
        else:
            st.error(f"❌ Syntax Error: {parsed.validation_error}")

st.write("")
col_sub1, col_sub2 = st.columns([2, 5])
with col_sub1:
    submit_btn = st.button("💾 Import & Save to Repository", type="primary", width='stretch')

if submit_btn:
    if not rep_name.strip():
        st.warning("Please specify a report name.")
    elif not sql_text_input.strip():
        st.warning("SQL query cannot be empty.")
    else:
        tags_list = [t.strip() for t in rep_tags.split(",") if t.strip()]
        report, dup_info = SQLRepositoryService.create_report(
            session=db_session,
            report_name=rep_name,
            sql_query=sql_text_input,
            database_id=selected_db_id,
            user=current_user,
            description=rep_desc,
            business_purpose=rep_purpose,
            category=rep_category,
            tags=tags_list
        )

        st.success(f"🎉 Report **{report.report_name}** successfully imported as **{report.report_code}**!")
        
        if dup_info["is_duplicate"]:
            st.warning(f"⚠️ Duplicate Detected: This SQL query is structurally identical to existing report '{dup_info['duplicate_report_name']}' ({dup_info['duplicate_report_code']}). Both copies are preserved.")

        st.info(f"Initial Status: **{report.status}** | Version: **v{report.version}** | Complexity: **{report.metadata_rel.complexity_level}**")
        st.session_state.selected_report_id = report.id
        if st.button("View Report Details"):
            st.switch_page("pages/4_📄_Report_Detail.py")

db_session.close()
