"""Module 2: SQL Repository Dashboard & Search.

Displays:
- Repository KPI Metrics (Total, Approved, Pending Review, Invalid, Archived)
- Category & Database Breakdowns
- Advanced Search and Facet Filtering
- Report Cards & Quick Actions
"""

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
from backend.database.connection_manager import connection_manager
from backend.database.models import User
from backend.services.sql_repository_service import SQLRepositoryService

st.set_page_config(page_title="SQL Knowledge Repository", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .kpi-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .kpi-num {
        font-size: 26px;
        font-weight: 700;
        color: #1E3A8A;
    }
    .kpi-lbl {
        font-size: 11px;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .status-badge {
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Session user setup
if "current_username" not in st.session_state:
    st.session_state.current_username = "admin"

db_session = SessionLocal()
current_user = db_session.query(User).filter(User.username == st.session_state.current_username).first()
if not current_user:
    current_user = db_session.query(User).first()

# Header
st.markdown("## 📚 Enterprise SQL Knowledge Repository")
st.markdown("*Transforming historical HR reporting logic, joins, and effective dating into verified enterprise knowledge.*")
st.divider()

# -------------------------------------------------------------
# 1. Repository KPI Dashboard
# -------------------------------------------------------------
stats = SQLRepositoryService.get_dashboard_stats(db_session, organization_id="org_default")

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    st.markdown(f'<div class="kpi-box"><div class="kpi-num">{stats["total_reports"]}</div><div class="kpi-lbl">Total Reports</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="kpi-box"><div class="kpi-num" style="color: #059669;">{stats["approved"]}</div><div class="kpi-lbl">Approved (RAG)</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="kpi-box"><div class="kpi-num" style="color: #D97706;">{stats["pending_review"]}</div><div class="kpi-lbl">Pending Review</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class="kpi-box"><div class="kpi-num" style="color: #DC2626;">{stats["invalid"]}</div><div class="kpi-lbl">Invalid Syntax</div></div>', unsafe_allow_html=True)
with k5:
    st.markdown(f'<div class="kpi-box"><div class="kpi-num" style="color: #64748B;">{stats["archived"]}</div><div class="kpi-lbl">Archived</div></div>', unsafe_allow_html=True)
with k6:
    st.markdown(f'<div class="kpi-box"><div class="kpi-num" style="color: #6366F1;">{stats["draft"]}</div><div class="kpi-lbl">Drafts</div></div>', unsafe_allow_html=True)

st.write("")

# -------------------------------------------------------------
# 2. Advanced Search & Filtering
# -------------------------------------------------------------
st.markdown("### 🔎 Repository Search & Filter")
col_s1, col_s2, col_s3, col_s4 = st.columns([3, 2, 2, 2])

with col_s1:
    search_q = st.text_input("Search reports, tables, columns, or SQL text:", placeholder="e.g. attrition, compensation, headcount...")
with col_s2:
    dbs = connection_manager.list_databases_safe()
    db_opts = ["All"] + [d["database_id"] for d in dbs]
    sel_db = st.selectbox("Database:", db_opts)
with col_s3:
    cat_opts = ["All", "Headcount", "Attrition", "Recruitment", "Attendance", "Leave", "Salary", "Compensation", "Performance", "Employee Demographics", "Department", "Job Role", "Location", "Tenure", "Other"]
    sel_cat = st.selectbox("Category:", cat_opts)
with col_s4:
    status_opts = ["All", "APPROVED", "PENDING_REVIEW", "DRAFT", "INVALID", "ARCHIVED", "REJECTED"]
    sel_status = st.selectbox("Status:", status_opts)

# Advanced toggles
with st.expander("⚙️ Advanced Filter Options"):
    adv1, adv2, adv3 = st.columns(3)
    with adv1:
        sel_comp = st.selectbox("Complexity Level:", ["All", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"])
    with adv2:
        eff_dating_filter = st.selectbox("Uses Effective Dating:", ["Any", "Yes", "No"])
    with adv3:
        sec_filter_opt = st.selectbox("Uses Security Filters:", ["Any", "Yes", "No"])

eff_dating_bool = True if eff_dating_filter == "Yes" else (False if eff_dating_filter == "No" else None)
sec_filter_bool = True if sec_filter_opt == "Yes" else (False if sec_filter_opt == "No" else None)

# Execute Search
reports = SQLRepositoryService.search_reports(
    session=db_session,
    query=search_q,
    database_id=sel_db if sel_db != "All" else None,
    category=sel_cat if sel_cat != "All" else None,
    status=sel_status if sel_status != "All" else None,
    complexity=sel_comp if sel_comp != "All" else None,
    uses_effective_dating=eff_dating_bool,
    uses_security_filter=sec_filter_bool,
    limit=50
)

st.write(f"Displaying **{len(reports)}** matching SQL reports:")

# Table Results
if reports:
    rows = []
    for r in reports:
        meta = r.metadata_rel
        rows.append({
            "Report Code": r.report_code,
            "Report Name": r.report_name,
            "Category": r.category,
            "Database": r.database_id,
            "Status": r.status,
            "Version": f"v{r.version}",
            "Complexity": meta.complexity_level if meta else "LOW",
            "Effective Dating": "YES" if (meta and meta.uses_effective_dating) else "NO",
            "Security Filter": "YES" if (meta and meta.uses_security_filter) else "NO",
            "Updated At": r.updated_at.strftime("%Y-%m-%d %H:%M") if r.updated_at else ""
        })
    st.dataframe(pd.DataFrame(rows), width='stretch')
else:
    st.info("No SQL reports found matching the specified filters.")

st.divider()

# Quick Navigation to detail
st.markdown("#### 📄 Open Report Details")
rep_code_options = [r.report_code for r in reports]
if rep_code_options:
    sel_code = st.selectbox("Select Report to Inspect:", rep_code_options)
    if st.button("Inspect Report Details"):
        chosen_rep = next(r for r in reports if r.report_code == sel_code)
        st.session_state.selected_report_id = chosen_rep.id
        st.switch_page("pages/4_📄_Report_Detail.py")
else:
    st.caption("Import or add reports to inspect their details.")

db_session.close()
