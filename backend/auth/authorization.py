"""Enterprise Authorization Engine (RBAC, ABAC, CLS, RLS, and Data Masking)."""

import hashlib
from typing import Dict, List, Any, Optional, Set
import pandas as pd
from sqlalchemy.orm import Session

from ..database.models import User
from ..database.models_auth import (
    Role,
    Permission,
    RolePermission,
    UserDatabaseAccess,
    ColumnPermission,
    RowAccessRule,
)
from .security_audit import SecurityAuditService

SYSTEM_PERMISSIONS = [
    ("sql:validate", "Validate SQL Query", "SQL", "Submit generated or custom SQL for safety validation"),
    ("sql:execute", "Execute Validated SQL", "SQL", "Execute approved SQL through execution engine"),
    ("sql:view_raw", "View Raw Unmasked SQL", "SQL", "View full raw SQL text and query execution plans"),
    ("db:select", "Select Database", "Database", "Select and switch between registered HR databases"),
    ("sql:upload", "Upload SQL", "SQL", "Upload custom SQL queries into repository"),
    ("schema:access", "Schema Access", "Schema", "Access and inspect database schemas"),
    ("rule:edit", "Edit Business Rules", "Rule", "Create and edit HR business rules"),
    ("rag:manage", "Manage RAG Knowledge", "RAG", "Manage RAG documents and vector index"),
    ("report:create", "Create Reports", "Report", "Build and save new HR reports"),
    ("report:execute", "Execute Reports", "Report", "Execute reports and retrieve query datasets"),
    ("report:view", "View Reports", "Report", "View saved reports and dashboards"),
    ("report:edit", "Edit Reports", "Report", "Update definitions, charts, and metrics of existing reports"),
    ("report:delete", "Delete Reports", "Report", "Delete or archive reports"),
    ("report:export", "Export Reports", "Report", "Export reports and query datasets to CSV/Excel/PDF"),
    ("report:share", "Share Reports", "Report", "Share reports with individual users or organizational roles"),
    ("sensitive:access", "Access Sensitive Data", "Security", "Access sensitive and unmasked employee HR data"),
    ("rule:view", "View Business Rules", "Rule", "View active business logic and validation rules"),
    ("rule:manage", "Manage Business Rules", "Rule", "Create, edit, approve, or deprecate business rules"),
    ("schema:view", "View Schema Catalog", "Schema", "Inspect database tables, columns, and relationships"),
    ("schema:manage", "Manage Schema Metadata", "Schema", "Edit human business terms and verify schema tables"),
    ("analytics:view", "View Analytics & Insights", "Analytics", "View automated statistical insights and trends"),
    ("pii:view_unmasked", "View Unmasked PII", "Security", "Access unmasked employee personal identifiable information"),
    ("admin:manage", "Administration", "Admin", "Administer system users, roles, and settings"),
    ("admin:users", "User Administration", "Admin", "Create users, assign roles, and manage credentials"),
    ("admin:audit", "View Security Audit Trail", "Admin", "Review system access, security, and execution logs"),
]

ALL_SYSTEM_PERMS = {p[0] for p in SYSTEM_PERMISSIONS}

DEFAULT_ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    # Phase 12 Canonical Roles
    "SUPER_ADMIN": ALL_SYSTEM_PERMS,
    "HR_ADMIN": {p for p in ALL_SYSTEM_PERMS if not p.startswith("admin:infra")},
    "HR_MANAGER": {
        "db:select", "schema:access", "schema:view", "rule:view", "rule:edit", "rule:manage",
        "report:create", "report:execute", "report:view", "report:edit", "report:export",
        "report:share", "sql:validate", "sql:execute", "analytics:view", "sensitive:access",
        "pii:view_unmasked"
    },
    "ANALYST": {
        "db:select", "schema:access", "schema:view", "rule:view", "report:create",
        "report:execute", "report:view", "report:edit", "report:export", "report:share",
        "sql:validate", "sql:execute", "analytics:view"
    },
    "REPORT_VIEWER": {
        "report:view", "report:execute", "report:export", "analytics:view"
    },
    # Lowercase aliases
    "super_admin": ALL_SYSTEM_PERMS,
    "admin": ALL_SYSTEM_PERMS,
    "hr_admin": {p for p in ALL_SYSTEM_PERMS if not p.startswith("admin:infra")},
    "hr_manager": {
        "db:select", "schema:access", "schema:view", "rule:view", "rule:edit", "rule:manage",
        "report:create", "report:execute", "report:view", "report:edit", "report:export",
        "report:share", "sql:validate", "sql:execute", "analytics:view", "sensitive:access",
        "pii:view_unmasked"
    },
    "hr_analyst": {
        "db:select", "schema:access", "schema:view", "rule:view", "report:create",
        "report:execute", "report:view", "report:edit", "report:export", "report:share",
        "sql:validate", "sql:execute", "analytics:view"
    },
    "analyst": {
        "db:select", "schema:access", "schema:view", "rule:view", "report:create",
        "report:execute", "report:view", "report:edit", "report:export", "report:share",
        "sql:validate", "sql:execute", "analytics:view"
    },
    "executive": {
        "report:view", "report:execute", "report:export", "analytics:view", "admin:audit"
    },
    "viewer": {
        "report:view", "report:execute"
    },
    "report_viewer": {
        "report:view", "report:execute", "report:export", "analytics:view"
    }
}

DEFAULT_SENSITIVE_COLUMNS = {
    "email": "partial",
    "phone": "partial",
    "first_name": "partial",
    "last_name": "partial",
    "ssn": "full",
    "tax_id": "full",
    "salary": "partial",
    "base_salary": "partial",
}


class AuthorizationService:
    """Central engine for RBAC, ABAC, database access, CLS, and RLS checks."""

    @classmethod
    def seed_system_roles_and_permissions(cls, db: Session):
        """Idempotently populates system roles, permissions, and initial associations."""
        perm_map = {}
        for code, name, category, desc in SYSTEM_PERMISSIONS:
            perm = db.query(Permission).filter(Permission.code == code).first()
            if not perm:
                perm = Permission(code=code, name=name, category=category, description=desc)
                db.add(perm)
                db.flush()
            perm_map[code] = perm

        for role_name, perm_codes in DEFAULT_ROLE_PERMISSIONS.items():
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                role = Role(
                    name=role_name,
                    description=f"Standard system role: {role_name.replace('_', ' ').title()}",
                    is_system=True
                )
                db.add(role)
                db.flush()

            # Associate permissions
            existing_perms = {
                rp.permission.code for rp in db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
            }
            for code in perm_codes:
                if code in perm_map and code not in existing_perms:
                    rp = RolePermission(role_id=role.id, permission_id=perm_map[code].id)
                    db.add(rp)

        db.commit()

    @classmethod
    def has_permission(cls, db: Session, user: User, permission_code: str) -> bool:
        """Determines if user possesses a specific permission code."""
        if not user or user.is_active is False:
            return False

        # Super admin shortcut
        if user.role in ("SUPER_ADMIN", "admin", "super_admin"):
            return True

        # Check DB role assignments
        role = db.query(Role).filter(Role.name == user.role).first()
        if not role:
            role = db.query(Role).filter(Role.name == user.role.upper()).first()
        if role:
            has_perm = db.query(RolePermission).join(Permission).filter(
                RolePermission.role_id == role.id,
                Permission.code == permission_code
            ).first() is not None
            if has_perm:
                return True

        # Fallback to system defaults if DB role not yet synced
        defaults = DEFAULT_ROLE_PERMISSIONS.get(user.role, set())
        if not defaults:
            defaults = DEFAULT_ROLE_PERMISSIONS.get(user.role.upper(), set())
        return permission_code in defaults

    @classmethod
    def can_access_database(
        cls,
        db: Session,
        user: User,
        database_id: str,
        mode: str = "read"
    ) -> bool:
        """
        ABAC check: determines whether user is cleared to access a target database.
        Admin has universal access.
        """
        if not user or user.is_active is False:
            return False

        if user.role == "admin":
            return True

        access = db.query(UserDatabaseAccess).filter(
            UserDatabaseAccess.user_id == user.id,
            UserDatabaseAccess.database_id == database_id
        ).first()

        if access:
            if mode == "read":
                return access.can_read
            elif mode == "write":
                return access.can_write
            elif mode == "execute":
                return access.can_execute
            return False

        # If no explicit restriction is defined, users can access standard default databases
        if database_id in ["sqlite_hr_default", "db_hr_analytics", "default"]:
            return True

        # Deny access by default for unassigned isolated enterprise databases
        SecurityAuditService.log_event(
            db=db,
            event_type="DATABASE_ACCESS_DENIED",
            status="BLOCKED",
            user_id=user.id,
            username=user.username,
            details={"database_id": database_id, "mode": mode}
        )
        return False

    @classmethod
    def get_column_permissions(
        cls,
        db: Session,
        user: User,
        database_id: str,
        table_name: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Retrieves Column-Level Security rules for a specific table.
        Returns dict: {column_name: {"is_allowed": bool, "is_masked": bool, "mask_type": str}}
        """
        perms = {}
        role = db.query(Role).filter(Role.name == user.role).first()

        # Query explicit rules from DB
        query = db.query(ColumnPermission).filter(
            ColumnPermission.database_id == database_id,
            ColumnPermission.table_name.ilike(table_name)
        )
        if role:
            query = query.filter((ColumnPermission.user_id == user.id) | (ColumnPermission.role_id == role.id))
        else:
            query = query.filter(ColumnPermission.user_id == user.id)

        for cp in query.all():
            perms[cp.column_name.lower()] = {
                "is_allowed": cp.is_allowed,
                "is_masked": cp.is_masked,
                "mask_type": cp.mask_type
            }

        # Check PII permission
        can_view_pii = cls.has_permission(db, user, "pii:view_unmasked")
        if not can_view_pii:
            for col, mask_t in DEFAULT_SENSITIVE_COLUMNS.items():
                if col not in perms:
                    perms[col] = {
                        "is_allowed": True,
                        "is_masked": True,
                        "mask_type": mask_t
                    }

        return perms

    @classmethod
    def get_row_security_filters(
        cls,
        db: Session,
        user: User,
        database_id: str,
        table_name: str
    ) -> List[str]:
        """
        Retrieves Row-Level Security (RLS) WHERE filter expressions.
        Replaces dynamic placeholders like {user.department_id} or {user.id}.
        """
        if user.role == "admin":
            return []

        filters = []
        role = db.query(Role).filter(Role.name == user.role).first()
        query = db.query(RowAccessRule).filter(
            RowAccessRule.database_id == database_id,
            RowAccessRule.table_name.ilike(table_name),
            RowAccessRule.is_active == True
        )
        if role:
            query = query.filter((RowAccessRule.user_id == user.id) | (RowAccessRule.role_id == role.id))
        else:
            query = query.filter(RowAccessRule.user_id == user.id)

        for rule in query.all():
            expr = rule.filter_expression
            expr = expr.replace("{user.id}", str(user.id))
            expr = expr.replace("{user.department_id}", str(user.department_id or "NULL"))
            expr = expr.replace("{user.username}", f"'{user.username}'")
            filters.append(expr)

        return filters

    @staticmethod
    def mask_value(val: Any, mask_type: str = "partial") -> Any:
        """Applies masking algorithms to sensitive values."""
        if val is None or pd.isna(val):
            return val

        str_val = str(val).strip()
        if not str_val:
            return str_val

        if mask_type == "full":
            return "******"
        elif mask_type == "null":
            return None
        elif mask_type == "hash":
            digest = hashlib.sha256(str_val.encode("utf-8")).hexdigest()[:8]
            return f"[HASH-{digest}]"
        elif mask_type == "partial":
            if "@" in str_val:
                parts = str_val.split("@", 1)
                prefix = parts[0]
                masked_prefix = f"{prefix[:2]}***" if len(prefix) >= 2 else "***"
                return f"{masked_prefix}@{parts[1]}"
            elif len(str_val) <= 2:
                return "***"
            elif len(str_val) <= 4:
                return str_val[0] + "***"
            else:
                return str_val[0] + "***" + str_val[-1]

        return "******"

    @classmethod
    def apply_column_masking(
        cls,
        df: pd.DataFrame,
        db: Session,
        user: User,
        database_id: str,
        table_name: str = ""
    ) -> pd.DataFrame:
        """Applies CLS masking rules to a result dataframe."""
        if df.empty or user.role == "admin" or cls.has_permission(db, user, "pii:view_unmasked"):
            return df

        masked_df = df.copy()
        cls_rules = cls.get_column_permissions(db, user, database_id, table_name)

        for col in masked_df.columns:
            col_lower = col.lower()
            rule = cls_rules.get(col_lower)
            if rule and rule.get("is_masked"):
                mask_t = rule.get("mask_type", "partial")
                masked_df[col] = masked_df[col].apply(lambda v: cls.mask_value(v, mask_t))
            elif col_lower in DEFAULT_SENSITIVE_COLUMNS:
                mask_t = DEFAULT_SENSITIVE_COLUMNS[col_lower]
                masked_df[col] = masked_df[col].apply(lambda v: cls.mask_value(v, mask_t))

        return masked_df
