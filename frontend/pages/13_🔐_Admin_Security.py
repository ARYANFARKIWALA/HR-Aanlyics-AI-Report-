"""Module 11: Admin Security, RBAC, ABAC, and Data Masking Dashboard.

Provides:
- User Management & Account Lockout Clearance
- Roles & Capabilities Matrix
- Database Access Control (ABAC Isolation)
- Column-Level Security (CLS) & Sensitive Field Masking
- Row-Level Security (RLS) Predicate Rules
- Security & Compliance Audit Log Inspector
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

from backend.auth.authorization import AuthorizationService
from backend.auth.password import hash_password, validate_password_strength
from backend.auth.sessions import SessionManager
from backend.database.connection import SessionLocal, init_db
from backend.database.models import Department, User
from backend.database.models_auth import (
    ColumnPermission,
    Permission,
    Role,
    RowAccessRule,
    SecurityAuditLog,
    UserDatabaseAccess,
)

st.set_page_config(
    page_title="Admin Security & Access - HR Analytics AI",
    page_icon="🔐",
    layout="wide"
)

st.title("🔐 Authentication & Authorization Governance")
st.caption("Module 11 — RBAC, ABAC Database Isolation, Column Masking, Row Security & Audit Logs")

init_db()
db = SessionLocal()
AuthorizationService.seed_system_roles_and_permissions(db)

# Tabs for management sections
tab_users, tab_roles, tab_db_access, tab_cls, tab_rls, tab_audit = st.tabs([
    "👥 User Directory",
    "🛡️ Roles & Permissions",
    "🗄️ Database Access (ABAC)",
    "👁️ Column Masking (CLS)",
    "🔍 Row Security (RLS)",
    "📜 Security Audit Trail"
])

# ----------------- 1. USER DIRECTORY -----------------
with tab_users:
    st.subheader("Enterprise Users & Account Status")
    users = db.query(User).all()
    user_rows = []
    for u in users:
        locked, remaining = SessionManager.is_account_locked(u)
        user_rows.append({
            "ID": u.id,
            "Username": u.username,
            "Full Name": u.full_name,
            "Email": u.email,
            "Role": u.role,
            "Dept ID": u.department_id,
            "Active": "✅" if u.is_active else "❌",
            "Lockout Status": f"🔒 Locked ({remaining}s left)" if locked else "🟢 Unlocked",
            "Failed Attempts": u.failed_login_attempts or 0
        })

    df_users = pd.DataFrame(user_rows)
    st.dataframe(df_users, width='stretch')

    col_unlock, col_create = st.columns([1, 1])
    with col_unlock:
        st.markdown("#### Account Lockout Resolution")
        locked_users = [u for u in users if SessionManager.is_account_locked(u)[0]]
        if locked_users:
            selected_unlock = st.selectbox("Select Locked User", [f"{u.id}: {u.username}" for u in locked_users])
            if st.button("🔓 Clear Lockout & Reset Counter"):
                uid = int(selected_unlock.split(":")[0])
                target = db.query(User).filter(User.id == uid).first()
                if target:
                    target.failed_login_attempts = 0
                    target.locked_until = None
                    db.commit()
                    st.success(f"Unlocked account for {target.username}!")
                    st.rerun()
        else:
            st.info("No accounts are currently locked out.")

    with col_create, st.expander("➕ Create New User"), st.form("create_user_form"):
                new_username = st.text_input("Username*")
                new_fullname = st.text_input("Full Name*")
                new_email = st.text_input("Email*")
                new_password = st.text_input("Password*", type="password")
                roles_list = [r.name for r in db.query(Role).all()]
                new_role = st.selectbox("Role*", roles_list if roles_list else ["hr_analyst", "hr_manager", "admin", "executive"])
                dept_opts = {f"{d.id}: {d.name}": d.id for d in db.query(Department).all()}
                dept_sel = st.selectbox("Department", ["None"] + list(dept_opts.keys()))

                if st.form_submit_button("Register User"):
                    if not new_username or not new_email or not new_password:
                        st.error("Please provide username, email, and password.")
                    else:
                        is_valid, msg = validate_password_strength(new_password)
                        if not is_valid:
                            st.error(f"Password error: {msg}")
                        else:
                            dept_id = dept_opts.get(dept_sel) if dept_sel != "None" else None
                            user_obj = User(
                                username=new_username,
                                full_name=new_fullname or new_username,
                                email=new_email,
                                hashed_password=hash_password(new_password),
                                role=new_role,
                                department_id=dept_id,
                                is_active=True
                            )
                            db.add(user_obj)
                            db.commit()
                            st.success(f"User '{new_username}' created successfully!")
                            st.rerun()

# ----------------- 2. ROLES & PERMISSIONS -----------------
with tab_roles:
    st.subheader("Role-Based Access Control (RBAC) Matrix")
    roles = db.query(Role).all()
    all_perms = db.query(Permission).all()

    matrix_data = []
    for r in roles:
        r_perms = {rp.permission.code for rp in r.permissions}
        row = {"Role": r.name, "Description": r.description}
        for p in all_perms:
            row[p.code] = "✅" if p.code in r_perms else "—"
        matrix_data.append(row)

    st.dataframe(pd.DataFrame(matrix_data), width='stretch')

# ----------------- 3. DATABASE ACCESS (ABAC) -----------------
with tab_db_access:
    st.subheader("Database Tenant & Catalog Permissions")
    grants = db.query(UserDatabaseAccess).all()
    grant_rows = []
    for g in grants:
        u = db.query(User).filter(User.id == g.user_id).first()
        grant_rows.append({
            "User": u.username if u else f"ID: {g.user_id}",
            "Database ID": g.database_id,
            "Can Read": "✅" if g.can_read else "❌",
            "Can Write": "✅" if g.can_write else "❌",
            "Can Execute SQL": "✅" if g.can_execute else "❌",
            "Granted By": g.granted_by,
            "Granted At": str(g.granted_at)
        })

    if grant_rows:
        st.dataframe(pd.DataFrame(grant_rows), width='stretch')
    else:
        st.info("No custom database access grants registered (Default databases accessible by standard roles).")

    with st.expander("➕ Grant / Modify Database Access"), st.form("grant_db_form"):
        u_choice = st.selectbox("User", [f"{u.id}: {u.username}" for u in users])
        db_choice = st.text_input("Database ID", value="sqlite_hr_default")
        c_read = st.checkbox("Can Read", value=True)
        c_write = st.checkbox("Can Write", value=False)
        c_exec = st.checkbox("Can Execute SQL", value=True)

        if st.form_submit_button("Save Database Access Rule"):
            uid = int(u_choice.split(":")[0])
            existing = db.query(UserDatabaseAccess).filter(
                UserDatabaseAccess.user_id == uid,
                UserDatabaseAccess.database_id == db_choice
            ).first()
            if existing:
                existing.can_read = c_read
                existing.can_write = c_write
                existing.can_execute = c_exec
            else:
                new_g = UserDatabaseAccess(
                    user_id=uid,
                    database_id=db_choice,
                    can_read=c_read,
                    can_write=c_write,
                    can_execute=c_exec,
                    granted_by="admin"
                )
                db.add(new_g)
            db.commit()
            st.success("Database access rule saved!")
            st.rerun()

# ----------------- 4. COLUMN-LEVEL SECURITY & MASKING -----------------
with tab_cls:
    st.subheader("Column-Level Security (CLS) & PII Obfuscation")
    rules = db.query(ColumnPermission).all()
    cls_rows = []
    for r in rules:
        target = f"Role: {r.role_id}" if r.role_id else f"User: {r.user_id}"
        cls_rows.append({
            "Database": r.database_id,
            "Table": r.table_name,
            "Column": r.column_name,
            "Target": target,
            "Is Allowed": "✅" if r.is_allowed else "❌ (Forbidden)",
            "Is Masked": "🛡️ Yes" if r.is_masked else "No",
            "Masking Type": r.mask_type
        })
    if cls_rows:
        st.dataframe(pd.DataFrame(cls_rows), width='stretch')
    else:
        st.info("Using standard system PII rules: Email, Phone, Names masked for non-PII roles.")

    with st.expander("➕ Define Column Masking / Allow Rule"), st.form("cls_form"):
        c_db = st.text_input("Database ID", value="sqlite_hr_default")
        c_tbl = st.text_input("Table Name", value="employees")
        c_col = st.text_input("Column Name", value="salary")
        c_role = st.selectbox("Apply to Role", [r.name for r in roles])
        c_allow = st.checkbox("Allow Column in SELECT", value=True)
        c_mask = st.checkbox("Mask Column Value", value=True)
        c_type = st.selectbox("Mask Type", ["partial", "full", "hash", "null"])

        if st.form_submit_button("Save CLS Rule"):
            target_role = db.query(Role).filter(Role.name == c_role).first()
            cp = ColumnPermission(
                database_id=c_db,
                table_name=c_tbl,
                column_name=c_col,
                role_id=target_role.id if target_role else None,
                is_allowed=c_allow,
                is_masked=c_mask,
                mask_type=c_type
            )
            db.add(cp)
            db.commit()
            st.success("Column security rule registered!")
            st.rerun()

# ----------------- 5. ROW-LEVEL SECURITY (RLS) -----------------
with tab_rls:
    st.subheader("Row-Level Security (RLS) Predicates")
    st.caption("Filters automatically injected into query WHERE clauses based on user department/attributes.")
    rls_rules = db.query(RowAccessRule).all()
    rls_rows = []
    for r in rls_rules:
        target = f"Role ID: {r.role_id}" if r.role_id else f"User ID: {r.user_id}"
        rls_rows.append({
            "Database": r.database_id,
            "Table": r.table_name,
            "Target": target,
            "Filter Predicate": r.filter_expression,
            "Description": r.description,
            "Active": "✅" if r.is_active else "❌"
        })
    if rls_rows:
        st.dataframe(pd.DataFrame(rls_rows), width='stretch')
    else:
        st.info("No custom row-level filters configured.")

    with st.expander("➕ Add Row-Level Filter Predicate"), st.form("rls_form"):
            r_db = st.text_input("Database ID", value="sqlite_hr_default")
            r_tbl = st.text_input("Table Name", value="employees")
            r_role = st.selectbox("Target Role", [r.name for r in roles])
            r_expr = st.text_input("Filter Expression", value="department_id = {user.department_id}")
            r_desc = st.text_input("Rule Description", value="Restrict manager access to their department only")

            if st.form_submit_button("Add Row Filter"):
                role_obj = db.query(Role).filter(Role.name == r_role).first()
                new_rule = RowAccessRule(
                    database_id=r_db,
                    table_name=r_tbl,
                    role_id=role_obj.id if role_obj else None,
                    filter_expression=r_expr,
                    description=r_desc,
                    is_active=True
                )
                db.add(new_rule)
                db.commit()
                st.success("Row security filter added!")
                st.rerun()

# ----------------- 6. SECURITY AUDIT TRAIL -----------------
with tab_audit:
    st.subheader("Security & Access Audit Trail")
    logs = db.query(SecurityAuditLog).order_by(SecurityAuditLog.created_at.desc()).limit(100).all()
    log_rows = []
    for l in logs:
        log_rows.append({
            "Timestamp (UTC)": str(l.created_at),
            "Event Type": l.event_type,
            "Status": l.status,
            "Username": l.username or "—",
            "IP Address": l.ip_address or "—",
            "Details": l.details or ""
        })
    if log_rows:
        st.dataframe(pd.DataFrame(log_rows), width='stretch')
    else:
        st.info("No security audit events recorded yet.")

db.close()
