"""Module 12: Streamlit Report Catalog, Sharing ACLs, Versioning & Multi-Format Export.

Provides:
- Enterprise Saved Reports Catalog & Search
- Version History & Non-Destructive Version Rollback
- Granular Role & User Access Control (VIEW, EXPORT, EDIT, ADMIN)
- Zero-Trust Execution Handshake (Module 7 -> Module 8)
- Sanitized Multi-Format Export (CSV, Excel, PDF) with CLS Masking
"""

import os
import sys

import pandas as pd
import streamlit as st

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database.connection import SessionLocal, init_db
from backend.database.models import User
from reports_lifecycle.execution_service import ReportExecutionService
from reports_lifecycle.export_service import ReportExportService
from reports_lifecycle.report_service import ReportLifecycleService
from reports_lifecycle.schemas import (
    ReportAccessCreateRequest,
    ReportCreateRequest,
    ReportRunRequest,
    ReportUpdateRequest,
)
from reports_lifecycle.sharing_service import ReportSharingService
from reports_lifecycle.version_service import ReportVersionService

st.set_page_config(
    page_title="Report Catalog & Export - HR Analytics AI",
    page_icon="📁",
    layout="wide"
)

init_db()
db = SessionLocal()

# User Context in Session State
if "current_user_name" not in st.session_state:
    st.session_state["current_user_name"] = "admin"

users = db.query(User).filter(User.is_active == True).all()
user_map = {u.username: u for u in users}

# Top bar navigation and user simulation
top_col1, top_col2, top_col3 = st.columns([3, 1, 1])
with top_col1:
    st.title("📁 Report Catalog & Export Center")
    st.caption("Module 12 — Lifecycle Management, Version Control, Sharing ACLs & Boardroom Exports")
with top_col2:
    selected_username = st.selectbox(
        "Active User (Persona):",
        options=list(user_map.keys()),
        index=list(user_map.keys()).index(st.session_state["current_user_name"]) if st.session_state["current_user_name"] in user_map else 0
    )
    st.session_state["current_user_name"] = selected_username
    current_user = user_map.get(selected_username)
with top_col3:
    if current_user:
        st.info(f"**Role:** `{current_user.role}`\n**ID:** `{current_user.id}`")

st.markdown("---")

tab_catalog, tab_manage, tab_versions, tab_sharing, tab_run = st.tabs([
    "📂 Report Catalog",
    "➕ Create / Edit Report",
    "🔄 Version History & Restore",
    "👥 Sharing & Access Control",
    "⚡ Run & Export"
])

# =========================================================================
# TAB 1: REPORT CATALOG
# =========================================================================
with tab_catalog:
    st.subheader("Enterprise Saved Reports")
    
    col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 1])
    with col_filter1:
        search_query = st.text_input("🔍 Search reports (title, description, category):", placeholder="e.g. Headcount, Comp, Turnover")
    with col_filter2:
        category_filter = st.selectbox("Filter by Category:", ["All", "General HR", "Headcount", "Compensation", "Attrition", "Diversity", "Performance"])
    with col_filter3:
        include_archived = st.checkbox("Include Archived", value=False)

    reports = ReportLifecycleService.list_reports(
        db=db,
        user=current_user,
        category=category_filter,
        search=search_query,
        include_archived=include_archived
    )

    if not reports:
        st.warning("No accessible reports found matching current filters.")
    else:
        st.write(f"Showing **{len(reports)}** accessible report(s):")
        
        rep_rows = []
        for r in reports:
            rep_rows.append({
                "Report ID": r.report_id,
                "Title": r.title,
                "Category": r.category,
                "Version": f"v{r.current_version}",
                "Author": r.author_username or "System",
                "Your Access": getattr(r, "user_access_level", "VIEW"),
                "Archived": "Yes" if r.is_archived else "No",
                "Last Updated": r.updated_at.strftime("%Y-%m-%d %H:%M") if r.updated_at else ""
            })
        
        rep_df = pd.DataFrame(rep_rows)
        st.dataframe(rep_df, width='stretch')

        selected_rep_id = st.selectbox(
            "Select a Report to inspect / work with:",
            options=[r.report_id for r in reports],
            format_func=lambda rid: f"{rid} - {next((r.title for r in reports if r.report_id == rid), '')}"
        )
        if selected_rep_id:
            st.session_state["selected_report_id"] = selected_rep_id

# Retrieve currently selected report
active_report_id = st.session_state.get("selected_report_id")
active_report = None
if active_report_id:
    try:
        active_report = ReportLifecycleService.get_report(db, active_report_id, current_user)
    except Exception as e:
        st.error(f"Could not load report '{active_report_id}': {e}")

# =========================================================================
# TAB 2: CREATE / EDIT REPORT
# =========================================================================
with tab_manage:
    st.subheader("Report Configuration & Metadata")

    mode = st.radio("Mode:", ["Edit Selected Report", "Create New Report"], horizontal=True)

    if mode == "Create New Report":
        st.markdown("##### ➕ Create New Saved Report")
        with st.form("create_report_form"):
            new_title = st.text_input("Report Title *", placeholder="e.g. Annual Department Turnover Summary")
            new_desc = st.text_area("Description", placeholder="Summary of what this report analyzes...")
            new_cat = st.selectbox("Category", ["General HR", "Headcount", "Compensation", "Attrition", "Diversity", "Performance"])
            new_db = st.text_input("Database ID", value="sqlite_hr_default")
            new_sql = st.text_area("SQL Query *", value="SELECT department, count(*) as headcount FROM employees GROUP BY department;", height=150)
            new_layout = st.text_area("Layout Config (JSON)", value='{"charts": [{"type": "bar", "x": "department", "y": "headcount"}]}', height=100)

            submitted = st.form_submit_button("Create Saved Report", type="primary")
            if submitted:
                if not new_title or not new_sql:
                    st.error("Title and SQL Query are required.")
                else:
                    try:
                        req = ReportCreateRequest(
                            title=new_title,
                            description=new_desc,
                            category=new_cat,
                            database_id=new_db,
                            sql_query=new_sql,
                            layout_config=new_layout
                        )
                        created = ReportLifecycleService.create_report(db, req, user=current_user)
                        st.success(f"Report '{created.title}' created successfully with ID: `{created.report_id}` (v1)")
                        st.session_state["selected_report_id"] = created.report_id
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create report: {e}")

    else:
        if not active_report:
            st.info("Select a report in the Catalog tab to edit.")
        else:
            user_level = getattr(active_report, "user_access_level", "NONE")
            st.markdown(f"##### ✏️ Edit: **{active_report.title}** (`{active_report.report_id}` - v{active_report.current_version})")
            st.caption(f"Your Access Level: **{user_level}** | Author: **{active_report.author_username}**")

            can_edit = ReportSharingService.can_edit(user_level)
            can_admin = ReportSharingService.can_admin(user_level)

            if not can_edit:
                st.warning("You have VIEW-only clearance on this report. Changes cannot be saved.")

            with st.form("edit_report_form"):
                edit_title = st.text_input("Title", value=active_report.title, disabled=not can_edit)
                edit_desc = st.text_area("Description", value=active_report.description or "", disabled=not can_edit)
                edit_cat = st.selectbox(
                    "Category",
                    ["General HR", "Headcount", "Compensation", "Attrition", "Diversity", "Performance"],
                    index=["General HR", "Headcount", "Compensation", "Attrition", "Diversity", "Performance"].index(active_report.category) if active_report.category in ["General HR", "Headcount", "Compensation", "Attrition", "Diversity", "Performance"] else 0,
                    disabled=not can_edit
                )
                edit_sql = st.text_area("SQL Query", value=active_report.sql_query, height=150, disabled=not can_edit)
                edit_summary = st.text_input("Summary of Changes for Version Snapshot", placeholder="e.g. Added department filter and average salary", disabled=not can_edit)

                save_btn = st.form_submit_button("Save Changes (Bump Version)", type="primary", disabled=not can_edit)
                if save_btn:
                    try:
                        upd_req = ReportUpdateRequest(
                            title=edit_title,
                            description=edit_desc,
                            category=edit_cat,
                            sql_query=edit_sql,
                            change_summary=edit_summary or f"Updated to version {active_report.current_version + 1}"
                        )
                        upd = ReportLifecycleService.update_report(db, active_report.report_id, upd_req, user=current_user)
                        st.success(f"Report updated to version v{upd.current_version}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("📋 Duplicate Report"):
                    try:
                        dup = ReportLifecycleService.duplicate_report(db, active_report.report_id, current_user)
                        st.success(f"Duplicated as: `{dup.report_id}`")
                        st.session_state["selected_report_id"] = dup.report_id
                        st.rerun()
                    except Exception as e:
                        st.error(f"Duplicate failed: {e}")
            with col_b:
                if can_admin:
                    btn_label = "📦 Unarchive Report" if active_report.is_archived else "📦 Archive Report"
                    if st.button(btn_label):
                        try:
                            ReportLifecycleService.archive_report(db, active_report.report_id, current_user, archive=not active_report.is_archived)
                            st.success("Archive status updated.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
            with col_c:
                if can_admin and st.button("🗑️ Delete Report (Soft-Delete)", type="secondary"):
                    try:
                        ReportLifecycleService.delete_report(db, active_report.report_id, current_user)
                        st.warning(f"Report '{active_report.report_id}' deleted.")
                        st.session_state["selected_report_id"] = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

# =========================================================================
# TAB 3: VERSION HISTORY & NON-DESTRUCTIVE RESTORE
# =========================================================================
with tab_versions:
    st.subheader("Version Snapshots & Rollback")
    if not active_report:
        st.info("Select a report in the Catalog tab to view its versions.")
    else:
        st.markdown(f"Version history for **{active_report.title}** (`{active_report.report_id}`):")
        versions = ReportVersionService.list_versions(db, active_report)

        ver_list = []
        for v in versions:
            ver_list.append({
                "Version": f"v{v.version_number}",
                "Title": v.title,
                "Modified By": v.modified_by_username or "System",
                "Change Summary": v.change_summary or "Snapshot",
                "Timestamp": v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else ""
            })
        st.dataframe(pd.DataFrame(ver_list), width='stretch')

        selected_ver = st.selectbox(
            "Inspect Historical Version:",
            options=[v.version_number for v in versions],
            format_func=lambda vn: f"Version {vn}"
        )
        target_v = next((v for v in versions if v.version_number == selected_ver), None)
        if target_v:
            st.markdown(f"**SQL Query at v{target_v.version_number}:**")
            st.code(target_v.sql_query, language="sql")

            can_edit = ReportSharingService.can_edit(getattr(active_report, "user_access_level", "NONE"))
            if st.button(f"🔄 Non-Destructively Restore to Version {target_v.version_number}", disabled=not can_edit):
                try:
                    restored = ReportVersionService.restore_version(db, active_report, target_v.version_number, current_user)
                    st.success(f"Restored! New version created: v{restored.current_version}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Restore failed: {e}")

# =========================================================================
# TAB 4: SHARING & ACCESS CONTROL (ACLS)
# =========================================================================
with tab_sharing:
    st.subheader("Report Sharing & Granular Access Control")
    if not active_report:
        st.info("Select a report in the Catalog tab to manage sharing.")
    else:
        st.markdown(f"Sharing permissions for **{active_report.title}**:")
        user_level = getattr(active_report, "user_access_level", "NONE")
        can_admin = ReportSharingService.can_admin(user_level)

        rules = ReportSharingService.list_access_rules(db, active_report)
        rule_data = []
        for r in rules:
            target_desc = f"User ID: {r.user_id}" if r.user_id else f"Role: {r.role_name}"
            rule_data.append({
                "Rule ID": r.id,
                "Recipient": target_desc,
                "Access Level": r.access_level,
                "Granted By": r.granted_by or "system",
                "Created At": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else ""
            })
        st.dataframe(pd.DataFrame(rule_data), width='stretch')

        if can_admin:
            st.markdown("##### ➕ Grant or Update Access Rule")
            with st.form("grant_access_form"):
                target_type = st.radio("Share with:", ["Role", "Individual User"], horizontal=True)
                target_user = None
                target_role = None
                if target_type == "Role":
                    target_role = st.selectbox("Select Role:", ["hr_analyst", "hr_manager", "executive", "viewer", "* (All Users)"])
                    if target_role == "* (All Users)":
                        target_role = "*"
                else:
                    target_user = st.selectbox("Select User:", options=users, format_func=lambda u: f"{u.username} ({u.full_name} - {u.role})")

                access_choice = st.selectbox("Access Level:", ["VIEW", "EXPORT", "EDIT", "ADMIN"])
                grant_btn = st.form_submit_button("Grant Access", type="primary")
                if grant_btn:
                    try:
                        req = ReportAccessCreateRequest(
                            user_id=target_user.id if target_user else None,
                            role_name=target_role,
                            access_level=access_choice
                        )
                        ReportSharingService.grant_access(db, active_report, req, current_user)
                        st.success("Access granted successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to grant access: {e}")

            if rules:
                st.markdown("##### 🗑️ Revoke Access Rule")
                rev_id = st.selectbox("Select Rule ID to revoke:", options=[r.id for r in rules])
                if st.button("Revoke Rule", type="secondary"):
                    try:
                        ReportSharingService.revoke_access(db, active_report, rev_id)
                        st.success("Rule revoked.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to revoke rule: {e}")
        else:
            st.info("ADMIN clearance is required to modify sharing rules.")

# =========================================================================
# TAB 5: RUN & EXPORT
# =========================================================================
with tab_run:
    st.subheader("Secure Re-run & Sanitized Boardroom Export")
    if not active_report:
        st.info("Select a report in the Catalog tab to run and export.")
    else:
        user_level = getattr(active_report, "user_access_level", "NONE")
        can_export = ReportSharingService.can_export(user_level)

        st.markdown(f"Target SQL for **{active_report.title}** (`v{active_report.current_version}`):")
        st.code(active_report.sql_query, language="sql")

        col_run1, col_run2 = st.columns([2, 3])
        with col_run1:
            run_limit = st.slider("Row Limit Cap:", min_value=10, max_value=1000, value=100, step=10)
            exec_btn = st.button("🚀 Run Report (Module 7 & 8 Gate)", type="primary")

        if exec_btn:
            with st.spinner("Validating SQL AST, verifying safety, and executing with type preservation..."):
                run_req = ReportRunRequest(limit=run_limit)
                run_res = ReportExecutionService.run_report(db, active_report, current_user, run_req=run_req)

                if run_res.status == "SUCCESS":
                    st.success(f"Execution Succeeded! Rows: **{run_res.row_count}** | Time: **{run_res.duration_ms:.2f}ms**")
                    st.info(f"🔑 **Validation ID:** `{run_res.validation_id}` | ⚡ **Execution ID:** `{run_res.execution_id}`")

                    if run_res.rows:
                        df_res = pd.DataFrame(run_res.rows)
                        st.dataframe(df_res, width='stretch')

                        # Stash data in session state for export
                        st.session_state["last_run_cols"] = run_res.columns
                        st.session_state["last_run_rows"] = run_res.rows
                    else:
                        st.warning("Query returned 0 rows.")
                else:
                    st.error(f"Execution Failed: {run_res.error or run_res.status}")

        # Export section
        if st.session_state.get("last_run_rows"):
            st.markdown("---")
            st.markdown("#### 📥 Download Sanitized Export")
            if not can_export:
                st.warning("Your report access level does not permit EXPORT. Contact the report owner.")
            else:
                cols = st.session_state["last_run_cols"]
                rows = st.session_state["last_run_rows"]

                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1:
                    csv_data = ReportExportService.export_csv(active_report, cols, rows, user=current_user)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"{active_report.title.replace(' ', '_')}_{active_report.report_id}.csv",
                        mime="text/csv",
                        width='stretch'
                    )
                with col_e2:
                    excel_data = ReportExportService.export_excel(active_report, cols, rows, user=current_user)
                    st.download_button(
                        label="📥 Download Excel (.xlsx)",
                        data=excel_data,
                        file_name=f"{active_report.title.replace(' ', '_')}_{active_report.report_id}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width='stretch'
                    )
                with col_e3:
                    pdf_data = ReportExportService.export_pdf(active_report, cols, rows, user=current_user)
                    st.download_button(
                        label="📥 Download PDF Document",
                        data=pdf_data,
                        file_name=f"{active_report.title.replace(' ', '_')}_{active_report.report_id}.pdf",
                        mime="application/pdf",
                        width='stretch'
                    )

        # Execution History
        st.markdown("---")
        st.markdown("#### 📜 Execution History Audit")
        executions = ReportExecutionService.list_executions(db, active_report, limit=10)
        if executions:
            exec_rows = []
            for ex in executions:
                exec_rows.append({
                    "Execution ID": ex.execution_id,
                    "Validation Token": ex.validation_id,
                    "User": ex.username or "Anonymous",
                    "Status": ex.status,
                    "Rows": ex.row_count,
                    "Duration (ms)": f"{ex.duration_ms:.2f}",
                    "Timestamp": ex.created_at.strftime("%Y-%m-%d %H:%M:%S") if ex.created_at else ""
                })
            st.dataframe(pd.DataFrame(exec_rows), width='stretch')
        else:
            st.caption("No historical executions recorded for this report yet.")

db.close()
