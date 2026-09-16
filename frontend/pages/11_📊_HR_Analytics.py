"""Module 9: Streamlit HR Analytics & Insight Engine Dashboard.

Provides:
- Deterministic HR KPI Calculators (Headcount, Turnover, Payroll, Diversity)
- Evidence-Based Narrative Executive Insights
- Cohort Segmentation & Cross-Tabulation
- Temporal Trends (YoY & MoM Trajectories)
- Statistical Outlier & Anomaly Inspector (IQR / Z-score)
- Data Quality & Completeness Scorecard
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

from analytics.schemas import AnalyticsRequest
from analytics.service import HRAnalyticsService
from backend.database.connection import SessionLocal, init_db
from backend.database.models import User
from backend.database.models_execution import QueryExecutionAuditLog
from query_execution.cache import QueryCacheManager

st.set_page_config(
    page_title="HR Analytics Engine - Enterprise HR",
    page_icon="📊",
    layout="wide"
)

st.title("📊 HR Analytics & Automated Insights Engine")
st.caption("Module 9 — Deterministic Mathematical Analytics, Statistical Outliers, Trend Analysis & Evidence Synthesis")

init_db()
db = SessionLocal()
service = HRAnalyticsService(db=db)

# ----------------- 1. DATASET SOURCE SELECTION -----------------
st.sidebar.subheader("Analytics Data Source")
source_mode = st.sidebar.radio(
    "Select Source",
    ["Recent Module 8 Execution", "Standard Enterprise Demo Cohort", "Upload CSV Dataset"]
)

active_df = pd.DataFrame()
selected_exec_id = None

if source_mode == "Recent Module 8 Execution":
    recent_execs = db.query(QueryExecutionAuditLog).filter(
        QueryExecutionAuditLog.status == "SUCCESS"
    ).order_by(QueryExecutionAuditLog.created_at.desc()).limit(15).all()

    if recent_execs:
        exec_opts = {
            f"{e.execution_id} ({e.row_count} rows, {e.database_id})": e.execution_id
            for e in recent_execs
        }
        sel_label = st.sidebar.selectbox("Choose Execution Result", list(exec_opts.keys()))
        selected_exec_id = exec_opts[sel_label]
        target_exec = next((e for e in recent_execs if e.execution_id == selected_exec_id), None)
        if target_exec:
            cached_res = QueryCacheManager.get(target_exec.database_id, target_exec.sql_hash)
            if cached_res:
                active_df, _, _ = cached_res
    else:
        st.sidebar.info("No query executions found. Using demo cohort.")
        source_mode = "Standard Enterprise Demo Cohort"

if source_mode == "Standard Enterprise Demo Cohort":
    # Construct a realistic rich HR dataset
    from backend.database.models import (
        CompensationHistory,
        Department,
        Employee,
        JobProfile,
    )
    emps = db.query(Employee).all()
    rows = []
    for e in emps:
        comp = db.query(CompensationHistory).filter(CompensationHistory.employee_id == e.id, CompensationHistory.is_current == True).first()
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
            "hire_date": str(e.hire_date),
            "base_salary": comp.base_salary if comp else 85000.0,
            "compa_ratio": comp.compa_ratio if comp else 1.0,
            "work_location": e.work_location
        })
    active_df = pd.DataFrame(rows)

elif source_mode == "Upload CSV Dataset":
    uploaded_file = st.sidebar.file_uploader("Upload HR CSV", type=["csv"])
    if uploaded_file:
        active_df = pd.read_csv(uploaded_file)

if active_df.empty:
    st.warning("No data available to analyze. Please select or execute a query first.")
    st.stop()

# Run Analytics Service
req = AnalyticsRequest(
    execution_id=selected_exec_id,
    dataset=active_df.to_dict(orient="records")
)
admin_user = db.query(User).filter(User.username == "admin").first()
result = service.analyze(req, user=admin_user)

# ----------------- 2. TOP KPI SNAPSHOT -----------------
st.subheader("🎯 Executive Human Capital KPIs")
k = result.kpis
c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Total Records", f"{k.total_records:,}")
c2.metric("Active Headcount", f"{k.active_headcount or '—'}")
c3.metric("Turnover Rate", f"{k.attrition_rate_pct}%" if k.attrition_rate_pct is not None else "—")
c4.metric("Average Salary", f"${k.avg_compensation:,.0f}" if k.avg_compensation else "—")
c5.metric("Total Payroll", f"${k.total_payroll:,.0f}" if k.total_payroll else "—")
c6.metric("Data Quality", f"{result.data_quality.quality_score}/100")

st.markdown("---")

# ----------------- 3. MULTI-TAB DEEP DIVE -----------------
tab_insights, tab_segments, tab_trends, tab_outliers, tab_corr, tab_quality = st.tabs([
    "💡 Narrative Insights",
    "📊 Cohort Segmentation",
    "📈 Temporal Trends",
    "🎯 Outliers & Anomalies",
    "🔗 Correlation Matrix",
    "📋 Quality & Column Profiles"
])

# Tab 1: Narrative Insights
with tab_insights:
    st.subheader("Automated Evidence-Based Insights")
    st.caption("Deterministic mathematical findings synthesized into executive summaries.")
    if result.insights:
        for ins in result.insights:
            badge_color = "🔴" if ins.insight_type == "ALERT" else ("🟢" if ins.insight_type == "BENCHMARK" else "🔵")
            with st.container():
                st.markdown(f"#### {badge_color} {ins.title} `[{ins.category}]`")
                st.write(ins.text)
                if ins.metric_citations:
                    with st.expander("🔍 Verified Mathematical Citations"):
                        st.json(ins.metric_citations)
                st.markdown("---")
    else:
        st.info("No actionable insights identified for this dataset.")

# Tab 2: Cohort Segmentation
with tab_segments:
    st.subheader("Multidimensional Cohort Breakdowns")
    if result.segmentations:
        for seg in result.segmentations:
            st.markdown(f"#### Sliced by: **{seg.dimension.replace('_', ' ').title()}**")
            seg_rows = []
            for seg_name, data in seg.segments.items():
                r = {"Segment": seg_name}
                r.update(data)
                seg_rows.append(r)
            st.dataframe(pd.DataFrame(seg_rows), width='stretch')
    else:
        st.info("No categorical dimensions found for cohort segmentation.")

# Tab 3: Temporal Trends
with tab_trends:
    st.subheader("Chronological Volume & Metric Trajectory")
    if result.trends:
        trend_rows = [t.model_dump() for t in result.trends]
        st.dataframe(pd.DataFrame(trend_rows), width='stretch')
    else:
        st.info("No chronological date column found for time-series trend calculation.")

# Tab 4: Statistical Outliers
with tab_outliers:
    st.subheader("Statistical Anomalies & Dispersion (IQR Method)")
    if result.outliers:
        st.warning(f"Detected **{len(result.outliers)}** records exceeding statistical dispersion boundaries.")
        outlier_rows = [o.model_dump() for o in result.outliers]
        st.dataframe(pd.DataFrame(outlier_rows), width='stretch')
    else:
        st.success("✅ No statistical outliers detected. Values lie within normal distribution boundaries.")

# Tab 5: Correlation Matrix
with tab_corr:
    st.subheader("Bivariate Correlation Analysis (Pearson)")
    if result.correlations:
        corr_rows = [c.model_dump() for c in result.correlations]
        st.dataframe(pd.DataFrame(corr_rows), width='stretch')
    else:
        st.info("Insufficient numeric columns for correlation analysis.")

# Tab 6: Quality & Column Profiles
with tab_quality:
    st.subheader("Data Quality & Column Profiles Scorecard")
    q = result.data_quality
    st.write(f"- **Overall Quality Index:** `{q.quality_score} / 100`")
    st.write(f"- **Cell Completeness:** `{q.completeness_pct}%`")
    st.write(f"- **Detected Anomalies:** `{q.anomaly_count}`")
    if q.issues:
        st.error("Detected Quality Issues:")
        for iss in q.issues:
            st.markdown(f"- {iss}")

    st.markdown("#### Column Summary Statistics")
    p_rows = [p.model_dump() for p in result.profiles]
    st.dataframe(pd.DataFrame(p_rows), width='stretch')

db.close()
