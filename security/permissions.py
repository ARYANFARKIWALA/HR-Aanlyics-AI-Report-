"""Role-Based Access Control (RBAC) and PII Data Masking."""

from typing import List, Dict, Any
import pandas as pd


class RBACManager:
    """Enforces fine-grained role capabilities."""

    ROLE_PERMISSIONS = {
        "admin": {
            "can_execute_raw_sql": True,
            "can_view_all_departments": True,
            "can_view_unmasked_pii": True,
            "can_view_audit_logs": True,
            "can_export_reports": True,
        },
        "hr_manager": {
            "can_execute_raw_sql": False,
            "can_view_all_departments": True,
            "can_view_unmasked_pii": True,
            "can_view_audit_logs": False,
            "can_export_reports": True,
        },
        "hr_analyst": {
            "can_execute_raw_sql": False,
            "can_view_all_departments": True,
            "can_view_unmasked_pii": False,  # Masks sensitive individual data
            "can_view_audit_logs": False,
            "can_export_reports": True,
        },
        "executive": {
            "can_execute_raw_sql": False,
            "can_view_all_departments": True,
            "can_view_unmasked_pii": False,
            "can_view_audit_logs": True,
            "can_export_reports": True,
        },
    }

    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        perms = cls.ROLE_PERMISSIONS.get(role, {})
        return perms.get(permission, False)


def mask_string(val: str) -> str:
    """Masks a string keeping initial letter."""
    if not val or len(val) <= 2:
        return "***"
    return val[0] + "***" + val[-1]


def mask_email(email: str) -> str:
    """Masks an email address."""
    if "@" not in email:
        return "***"
    name, domain = email.split("@", 1)
    return f"{name[:2]}***@{domain}"


def mask_pii_dataframe(df: pd.DataFrame, user_role: str) -> pd.DataFrame:
    """Masks PII columns (names, emails, phone) if user lacks unmasked permission."""
    if RBACManager.has_permission(user_role, "can_view_unmasked_pii"):
        return df

    masked_df = df.copy()
    for col in masked_df.columns:
        col_lower = col.lower()
        if col_lower in ["first_name", "last_name", "employee_name", "name"]:
            masked_df[col] = masked_df[col].astype(str).apply(mask_string)
        elif col_lower in ["email"]:
            masked_df[col] = masked_df[col].astype(str).apply(mask_email)
        elif col_lower in ["phone"]:
            masked_df[col] = "***-***-****"

    return masked_df
