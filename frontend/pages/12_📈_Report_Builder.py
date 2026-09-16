"""Module 10: Streamlit Interactive Report Builder & Visualizer.

Provides:
- Executive HR Dashboard Layouts & Pre-Configured Templates
- Interactive Global Filters (Department, Location, Status)
- Plotly Chart Rendering (Bar, Line, Donut, Box Plot, Scatter)
- Executive KPI Cards & Dynamic Callout Banners
- Formatted Tabular Reports with Pagination
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
import plotly.graph_objects as go
from backend.database.connection import SessionLocal, init_db
from backend.database.models import Employee, Department, JobProfile, CompensationHistory
from report_builder.schemas import ReportDefinition
from report_builder.service import ReportBuilderService
from report_builder.template_manager import TemplateManager

st.set_page_config(
    page_title="Report Builder - HR Analytics AI",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Report Builder & Visualization Engine")
st.caption("Module 10 — Executive Dashboards, Dynamic Multi-Filter Slicing, Plotly Visualizations & Template Architecture")

init_db()
db = SessionLocal()

# ----------------- 1. LOAD ENTERPRISE DATASET -----------------
@st.cache_data(ttl=60)
def load_rich_hr_data():
    emps = db.query(Employee).all()
    rows = []
    for e in emps:
        comp = db.query(CompensationHistory).filter(
            CompensationHistory.employee_id == e.id,
            CompensationHistory.is_current == True
        ).first()
        dept = db.query(Department).filter(Department.id == e.department_id).first()
        job = db.query(JobProfile).filter(JobProfile.id == e.job_profile_id).first()
        rows.append({
            "employee_id": e.employee_number,
            "first_name": e.first_name,
            "last_name": e.last_name,
            "department": dept.name if dept else "General",
            "job_title": job.title if job else "Staff",
            "job_family": job.job_family if job else "Operations",
            "gender": e.gender,
            "status": e.status,
            "attrition_type": e.attrition_type or "None",
            "hire_date": str(e.hire_date),
            "base_salary": comp.base_salary if comp else 85000.0,
            "compa_ratio": comp.compa_ratio if comp else 1.0,
            "work_location": e.work_location
        })
    return pd.DataFrame(rows)

base_df = load_rich_hr_data()

# ----------------- 2. SIDEBAR TEMPLATE & FILTERS -----------------
st.sidebar.subheader("📋 Report Templates")
templates = TemplateManager.list_templates()
tpl_options = {t["title"]: t["key"] for t in templates}
selected_tpl_title = st.sidebar.selectbox("Choose Layout Template", list(tpl_options.keys()), index=0)
selected_tpl_key = tpl_options[selected_tpl_title]

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Interactive Global Filters")

# Extract filter options
all_depts = sorted(list(base_df["department"].unique()))
all_locations = sorted(list(base_df["work_location"].unique()))
all_statuses = sorted(list(base_df["status"].unique()))

sel_depts = st.sidebar.multiselect("Department Filter", all_depts, default=[])
sel_locations = st.sidebar.multiselect("Work Location Filter", all_locations, default=[])
sel_status = st.sidebar.selectbox("Status Filter", ["All"] + all_statuses, index=0)

# Build active filter dictionary
active_filters = {}
if sel_depts:
    active_filters["department"] = sel_depts
if sel_locations:
    active_filters["work_location"] = sel_locations
if sel_status != "All":
    active_filters["status"] = sel_status

# ----------------- 3. BUILD REPORT -----------------
built_report = ReportBuilderService.build_from_template(
    template_key=selected_tpl_key,
    df=base_df,
    active_filters=active_filters
)

st.markdown(f"### {built_report.title}")
if built_report.description:
    st.caption(built_report.description)

# Display Active Filters Indicator
if active_filters:
    st.info(f"🔎 Active Filters: {active_filters} | Filtered Records: {built_report.row_count} of {len(base_df)}")

st.markdown("---")

# ----------------- 4. RENDER KPI CARDS -----------------
if built_report.kpi_cards:
    cols = st.columns(len(built_report.kpi_cards))
    for idx, kpi in enumerate(built_report.kpi_cards):
        with cols[idx]:
            st.metric(
                label=kpi.title,
                value=kpi.value,
                delta=kpi.delta_text,
                delta_color=kpi.delta_color,
                help=kpi.help_text
            )
    st.markdown("---")

# ----------------- 5. RENDER PLOTLY CHARTS -----------------
if built_report.charts:
    st.subheader("📊 Visual Analytics")
    # Display charts in 2-column grid
    for i in range(0, len(built_report.charts), 2):
        col_left, col_right = st.columns(2)
        with col_left:
            fig_dict = built_report.charts[i]
            fig = go.Figure(fig_dict)
            st.plotly_chart(fig, width='stretch')

        if i + 1 < len(built_report.charts):
            with col_right:
                fig_dict2 = built_report.charts[i + 1]
                fig2 = go.Figure(fig_dict2)
                st.plotly_chart(fig2, width='stretch')

# ----------------- 6. RENDER DATA TABLES -----------------
if built_report.tables:
    st.subheader("📋 Tabular Detail")
    for tbl in built_report.tables:
        st.markdown(f"#### {tbl['title']} ({tbl['total_rows']} matching rows)")
        if tbl["rows"]:
            df_tbl = pd.DataFrame(tbl["rows"])
            st.dataframe(df_tbl, width='stretch')
        else:
            st.info("No matching records found for active filters.")

db.close()
