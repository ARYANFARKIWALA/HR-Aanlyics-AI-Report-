"""Module 4: Streamlit Business Rule Management & Governance Dashboard.

Provides:
- Business Rule Dashboard (Total, Active, Review, Rejected, Low Confidence, Mandatory)
- Review & Approval Queue (Approve with comments, Reject with mandatory reason)
- Rule Explorer & Search (Filter by Category, Status, Priority, Table)
- Create & Edit Rule Studio (Automatic version increment on active rules)
- Conflict & Duplicate Scanner
- Rule Detection from Module 2 SQL Reports
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
from business_rules.conflict_detector import RuleConflictDetector
from business_rules.duplicate_detector import RuleDuplicateDetector
from business_rules.service import BusinessRuleService
from business_rules.validator import RuleValidationError

st.set_page_config(
    page_title="Business Rule Management - HR Analytics AI",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ HR Business Rule Management & Governance")
st.caption("Module 4 — Preserving Organizational Logic, Approvals, Immutability & Conflict Detection")

# Initialize DB session
init_db()
db = SessionLocal()
service = BusinessRuleService(db)

# Target Database Selector
registered_dbs = connection_manager.list_databases_safe()
db_options = [d["database_id"] for d in registered_dbs] if registered_dbs else ["sqlite_hr_default"]

col_db, col_btn = st.columns([4, 2])
with col_db:
    selected_db_id = st.selectbox("Target HR Database Connection", db_options, index=0)

with col_btn:
    st.write("")
    st.write("")
    if st.button("🔍 Mine Rules from SQL Repository", width='stretch'):
        with st.spinner("Analyzing Module 2 SQL reports for business rules..."):
            detected = service.detect_rules_from_sql_repository(database_id=selected_db_id)
            if detected:
                st.success(f"Discovered {len(detected)} candidate rules from existing SQL reports!")
            else:
                st.info("No new rules discovered or all report rules already registered.")
            st.rerun()

st.divider()

# -------------------------------------------------------------
# KPI Cards: Business Rules Dashboard
# -------------------------------------------------------------
stats = service.get_dashboard_stats(database_id=selected_db_id)

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    st.metric("Total Rules", stats["total_rules"])
with k2:
    st.metric("Active Rules", stats["active_rules"], help="Eligible for Module 5 RAG index")
with k3:
    st.metric("Under Review", stats["rules_under_review"], help="Detected from SQL or drafted")
with k4:
    st.metric("Low Confidence", stats["low_confidence_rules"], help="Confidence < 70% requires manual review")
with k5:
    st.metric("Mandatory Rules", stats["mandatory_rules"], help="Always enforced in generated queries")
with k6:
    st.metric("Rejected Rules", stats["rejected_rules"], help="Preserved for audit compliance")

st.divider()

# -------------------------------------------------------------
# Navigation Tabs
# -------------------------------------------------------------
tab_review, tab_explorer, tab_create, tab_conflicts, tab_audit = st.tabs([
    "📥 Review & Approval Queue",
    "📋 Rule Explorer & Search",
    "➕ Create / Edit Rule",
    "⚠️ Conflict & Duplicate Scanner",
    "🕒 Version History & Audit Trail"
])

# -------------------------------------------------------------
# TAB 1: Review & Approval Queue
# -------------------------------------------------------------
with tab_review:
    st.markdown("### 📥 Review & Approval Queue")
    st.caption("Review candidate rules detected from SQL reports or submitted by analysts. Low confidence rules require explicit approval.")

    pending_rules = service.get_rules(
        database_id=selected_db_id,
        status="DETECTED"
    ) + service.get_rules(
        database_id=selected_db_id,
        status="UNDER_REVIEW"
    )

    if not pending_rules:
        st.info("🎉 No rules currently pending review. All discovered rules have been processed!")
    else:
        st.write(f"Showing **{len(pending_rules)}** rule(s) awaiting approval:")
        for r in pending_rules:
            with st.container():
                st.markdown(f"#### `{r.rule_code}`: {r.rule_name}")
                c_p1, c_p2, c_p3 = st.columns([2, 2, 2])
                with c_p1:
                    st.write(f"**Category:** `{r.rule_type}`")
                    st.write(f"**Priority:** `{r.priority}` | **Mandatory:** {'Yes' if r.mandatory else 'No'}")
                with c_p2:
                    st.write(f"**Source:** `{r.source_type}` ({r.source_sql_report or 'Manual'})")
                    conf_pct = int(r.confidence_score * 100)
                    conf_color = "green" if conf_pct >= 90 else ("orange" if conf_pct >= 70 else "red")
                    st.markdown(f"**Confidence:** :{conf_color}[**{conf_pct}%**]")
                with c_p3:
                    st.write(f"**Target:** `{r.table_name or '*'}`.`{r.column_name or '*'}`")
                    st.write(f"**Version:** v{r.version}")

                st.code(r.rule_expression, language="sql")
                st.caption(f"**Business Meaning:** {r.natural_language_rule}")

                # Approval / Rejection Actions
                act_col1, act_col2 = st.columns(2)
                with act_col1, st.expander("✅ Approve Rule"), st.form(f"approve_form_{r.id}"):
                    appr_comment = st.text_input("Approval Comment", value="Confirmed and approved with HR policy.")
                    appr_btn = st.form_submit_button("Approve & Activate Rule")
                    if appr_btn:
                        service.approve_rule(r.id, comment=appr_comment, user_name="admin")
                        st.success(f"Rule {r.rule_code} approved and marked ACTIVE!")
                        st.rerun()

                with act_col2, st.expander("❌ Reject Rule"), st.form(f"reject_form_{r.id}"):
                    rej_reason = st.text_area("Rejection Reason (Mandatory)", placeholder="Explain why this rule is not general organizational policy...")
                    rej_btn = st.form_submit_button("Reject Rule")
                    if rej_btn:
                        if not rej_reason or len(rej_reason.strip()) < 3:
                            st.error("Rejection reason is mandatory.")
                        else:
                            service.reject_rule(r.id, reason=rej_reason, user_name="admin")
                            st.warning(f"Rule {r.rule_code} marked REJECTED.")
                            st.rerun()
                st.divider()

# -------------------------------------------------------------
# TAB 2: Rule Explorer & Search
# -------------------------------------------------------------
with tab_explorer:
    col_ef1, col_ef2, col_ef3, col_ef4 = st.columns([2, 2, 2, 3])
    with col_ef1:
        sel_st = st.selectbox("Status", ["ALL", "ACTIVE", "DETECTED", "UNDER_REVIEW", "REJECTED", "INACTIVE", "DEPRECATED"], index=0)
    with col_ef2:
        sel_tp = st.selectbox("Category", ["ALL", "EMPLOYEE_STATUS", "EFFECTIVE_DATING", "SALARY", "ATTENDANCE", "LEAVE", "DEPARTMENT", "SECURITY", "FILTER"], index=0)
    with col_ef3:
        sel_pr = st.selectbox("Priority", ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"], index=0)
    with col_ef4:
        search_term = st.text_input("Search rules by keyword, table, or expression...", placeholder="e.g. active, salary, status")

    filtered_rules = service.get_rules(
        database_id=selected_db_id,
        status=sel_st,
        rule_type=sel_tp,
        priority=sel_pr,
        search=search_term
    )

    if filtered_rules:
        df_rules = pd.DataFrame([
            {
                "ID": r.id,
                "Code": r.rule_code,
                "Name": r.rule_name,
                "Category": r.rule_type,
                "Status": r.status,
                "Priority": r.priority,
                "Mandatory": "✅ Yes" if r.mandatory else "No",
                "Expression": r.rule_expression,
                "Target Table": r.table_name or "-",
                "Version": f"v{r.version}"
            }
            for r in filtered_rules
        ])
        st.dataframe(df_rules, width='stretch', hide_index=True)

        st.markdown("#### 🔍 Rule Detail View")
        rule_choices = {f"{r.rule_code}: {r.rule_name}": r.id for r in filtered_rules}
        sel_r_label = st.selectbox("Select Rule to Inspect", list(rule_choices.keys()))
        selected_r_id = rule_choices[sel_r_label]
        detail = service.get_rule_detail(selected_r_id)

        if detail:
            st.json(detail)
    else:
        st.info("No business rules matched the selected filters.")

# -------------------------------------------------------------
# TAB 3: Create / Edit Rule
# -------------------------------------------------------------
with tab_create:
    st.markdown("### ➕ Create or Edit HR Business Rule")
    st.caption("Define official organizational rules. Active rules will create immutable new versions on edit.")

    with st.form("create_rule_form"):
        rc1, rc2 = st.columns(2)
        with rc1:
            r_name = st.text_input("Rule Name *", placeholder="e.g. Active Employee Rule")
            r_type = st.selectbox(
                "Rule Category *",
                ["EMPLOYEE_STATUS", "EFFECTIVE_DATING", "SALARY", "ATTENDANCE", "LEAVE", "ATTRITION", "DEPARTMENT", "LOCATION", "JOB", "SECURITY", "DATA_ACCESS", "DATE", "CALCULATION", "FILTER", "AGGREGATION", "CUSTOM"]
            )
            r_priority = st.selectbox("Priority *", ["MEDIUM", "HIGH", "CRITICAL", "LOW"], index=1)
            r_mandatory = st.checkbox("Mandatory Rule (Must be enforced in generated queries)", value=True)
            r_scope = st.selectbox("Scope", ["TABLE", "COLUMN", "GLOBAL", "DATABASE", "REPORT", "ROLE"])

        with rc2:
            r_table = st.text_input("Target Table Name", placeholder="e.g. employees")
            r_column = st.text_input("Target Column Name", placeholder="e.g. status")
            r_expr = st.text_area("SQL / Logical Filter Expression *", placeholder="e.g. employees.status = 'ACTIVE'")
            r_nl = st.text_area("Natural Language Definition *", placeholder="e.g. An employee is considered active when status is ACTIVE.")

        submit_rule = st.form_submit_button("Create Business Rule", type="primary")

        if submit_rule:
            try:
                created = service.create_rule({
                    "rule_name": r_name,
                    "rule_type": r_type,
                    "rule_expression": r_expr,
                    "natural_language_rule": r_nl,
                    "priority": r_priority,
                    "mandatory": r_mandatory,
                    "scope": r_scope,
                    "table_name": r_table.strip() if r_table else None,
                    "column_name": r_column.strip() if r_column else None,
                    "database_id": selected_db_id,
                    "status": "ACTIVE"
                }, user_name="admin")
                st.success(f"Created rule {created.rule_code} (v{created.version}) successfully!")
                st.rerun()
            except RuleValidationError as ve:
                st.error(f"Validation Error: {ve}")
            except Exception as ex:
                st.error(f"Error creating rule: {ex}")

# -------------------------------------------------------------
# TAB 4: Conflict & Duplicate Scanner
# -------------------------------------------------------------
with tab_conflicts:
    st.markdown("### ⚠️ Rule Conflict & Duplicate Scanner")
    st.caption("Detects contradictory predicates on identical columns and semantic duplicates across active rules.")

    with st.form("conflict_test_form"):
        sc1, sc2 = st.columns(2)
        with sc1:
            test_expr = st.text_input("Candidate Expression", value="employees.status = 'INACTIVE'")
            test_tbl = st.text_input("Table", value="employees")
            test_col = st.text_input("Column", value="status")
        with sc2:
            test_nl = st.text_area("Candidate Natural Language", value="An employee is active when status equals ACTIVE.")

        scan_btn = st.form_submit_button("Run Conflict & Duplicate Scan")

        if scan_btn:
            conflicts = RuleConflictDetector.detect_conflicts(
                candidate_rule={
                    "rule_expression": test_expr,
                    "table_name": test_tbl,
                    "column_name": test_col,
                    "database_id": selected_db_id
                },
                db=db,
                database_id=selected_db_id
            )
            duplicates = RuleDuplicateDetector.detect_duplicates(
                candidate_rule={
                    "rule_expression": test_expr,
                    "natural_language_rule": test_nl,
                    "database_id": selected_db_id
                },
                db=db,
                database_id=selected_db_id
            )

            if conflicts:
                st.error(f"⚠️ {len(conflicts)} Potential Conflict(s) Detected:")
                for c in conflicts:
                    st.warning(f"Conflicts with `{c['conflicting_rule_code']}` ({c['conflicting_rule_name']}): {c['reason']}")
            else:
                st.success("✅ No logical conflicts found with active rules.")

            if duplicates:
                st.info(f"ℹ️ {len(duplicates)} Duplicate/Similar Rule(s) Found:")
                for d in duplicates:
                    st.write(f"- Matches `{d['existing_rule_code']}` ({d['existing_rule_name']}) with similarity score: **{int(d['similarity_score'] * 100)}%**")
            else:
                st.success("✅ No duplicate rules found.")

# -------------------------------------------------------------
# TAB 5: Version History & Audit Trail
# -------------------------------------------------------------
with tab_audit:
    st.markdown("### 🕒 Version History & Audit Trail")
    st.caption("Tracks all version progressions and administrative actions (Create, Edit, Approve, Reject, Activate).")

    all_current = service.get_rules(database_id=selected_db_id)
    if all_current:
        rule_map = {f"{r.rule_code}: {r.rule_name} (v{r.version})": r.id for r in all_current}
        chosen_lbl = st.selectbox("Choose Rule to Inspect History", list(rule_map.keys()), key="audit_rule_sel")
        chosen_id = rule_map[chosen_lbl]

        detail = service.get_rule_detail(chosen_id)
        if detail:
            st.markdown("#### 📜 Version Progression")
            st.dataframe(pd.DataFrame(detail.get("versions", [])), width='stretch', hide_index=True)

            st.markdown("#### 🛡️ Compliance Audit Trail")
            st.dataframe(pd.DataFrame(detail.get("audit_trail", [])), width='stretch', hide_index=True)

db.close()
