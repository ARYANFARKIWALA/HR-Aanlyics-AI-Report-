"""Unit tests for Authentication, JWT, RBAC, and PII Data Masking."""

import pytest
import pandas as pd
from backend.auth.jwt_handler import hash_password, verify_password, create_access_token, decode_access_token
from security.permissions import RBACManager, mask_pii_dataframe


def test_password_hashing():
    raw = "StrongEnterprisePassword!2026"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_flow():
    payload = {"sub": "analyst", "role": "hr_analyst", "id": 3}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "analyst"
    assert decoded["role"] == "hr_analyst"


def test_rbac_permissions():
    assert RBACManager.has_permission("admin", "can_view_unmasked_pii") is True
    assert RBACManager.has_permission("hr_analyst", "can_view_unmasked_pii") is False
    assert RBACManager.has_permission("executive", "can_export_reports") is True


def test_pii_masking():
    df = pd.DataFrame([
        {"first_name": "Sarah", "last_name": "Chen", "email": "sarah.chen@enterprise-hr.internal", "salary": 160000},
        {"first_name": "Marcus", "last_name": "Vance", "email": "marcus.vance@enterprise-hr.internal", "salary": 140000}
    ])

    # Analyst role -> should mask
    masked_df = mask_pii_dataframe(df, "hr_analyst")
    assert masked_df["first_name"].iloc[0] == "S***h"
    assert masked_df["last_name"].iloc[0] == "C***n"
    assert "@enterprise-hr.internal" in masked_df["email"].iloc[0]
    assert masked_df["email"].iloc[0].startswith("sa***@")

    # Admin role -> should NOT mask
    unmasked_df = mask_pii_dataframe(df, "admin")
    assert unmasked_df["first_name"].iloc[0] == "Sarah"
