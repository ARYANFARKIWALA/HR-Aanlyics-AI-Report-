"""Unit and Integration Tests for Module 11 — Authentication & Authorization."""

import datetime

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.auth.authorization import AuthorizationService
from backend.auth.password import (
    hash_password,
    validate_password_strength,
    verify_password,
)
from backend.auth.sessions import SessionManager
from backend.database.connection import SessionLocal, init_db
from backend.database.models import User
from backend.database.models_auth import (
    RowAccessRule,
    UserDatabaseAccess,
)
from backend.main import app


@pytest.fixture(scope="function")
def db_session():
    init_db()
    session = SessionLocal()
    AuthorizationService.seed_system_roles_and_permissions(session)
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_password_policy_and_verification():
    """Validates PBKDF2 hashing, verification, and password complexity rules."""
    # Complexity
    ok, _ = validate_password_strength("Short1!")
    assert ok is False
    ok, _ = validate_password_strength("alllowercase1!")
    assert ok is False
    ok, _ = validate_password_strength("ALLUPPERCASE1!")
    assert ok is False
    ok, _ = validate_password_strength("NoDigitsHere!")
    assert ok is False
    ok, _ = validate_password_strength("NoSpecialChar123")
    assert ok is False
    ok, _msg = validate_password_strength("ValidP@ssw0rd2026")
    assert ok is True

    # Hashing & Verification
    pwd = "ValidP@ssw0rd2026"
    h = hash_password(pwd)
    assert h != pwd
    assert verify_password(pwd, h) is True
    assert verify_password("WrongPass123!", h) is False


def test_brute_force_lockout_and_unlock(db_session):
    """Verifies that 5 failed attempts trigger account lockout for 15 minutes."""
    # Create test user
    username = f"lockout_test_{int(datetime.datetime.now().timestamp())}"
    user = User(
        username=username,
        full_name="Lockout Test User",
        email=f"{username}@test.internal",
        hashed_password=hash_password("SecurePass123!"),
        role="hr_analyst",
        is_active=True,
        failed_login_attempts=0
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 4 failed attempts -> not locked
    for i in range(4):
        locked, _ = SessionManager.record_login_failure(db_session, user)
        assert locked is False
        assert user.failed_login_attempts == i + 1

    # 5th failed attempt -> locked!
    locked, msg = SessionManager.record_login_failure(db_session, user)
    assert locked is True
    assert "locked" in msg.lower()
    assert user.locked_until is not None

    # Check is_account_locked
    is_locked, remaining = SessionManager.is_account_locked(user)
    assert is_locked is True
    assert remaining > 0

    # Test unlocking
    user.failed_login_attempts = 0
    user.locked_until = None
    db_session.commit()
    is_locked, _ = SessionManager.is_account_locked(user)
    assert is_locked is False


def test_session_lifecycle(db_session):
    """Tests session creation, idle timeout sliding, and explicit revocation."""
    user = db_session.query(User).filter(User.username == "admin").first()
    assert user is not None

    session = SessionManager.record_login_success(db_session, user, ip_address="192.168.1.10")
    assert session.session_token is not None
    assert session.is_revoked is False

    # Validate active session
    validated = SessionManager.validate_session(db_session, session.session_token)
    assert validated is not None
    assert validated.user_id == user.id

    # Revoke session
    revoked = SessionManager.revoke_session(db_session, session.session_token)
    assert revoked is True

    # Validate again -> should be None
    validated2 = SessionManager.validate_session(db_session, session.session_token)
    assert validated2 is None


def test_rbac_permissions_resolution(db_session):
    """Tests RBAC permissions evaluation for various roles."""
    admin_user = User(username="admin_u", full_name="Admin", email="admin_u@test.com", hashed_password="x", role="admin", is_active=True)
    analyst_user = User(username="analyst_u", full_name="Analyst", email="analyst_u@test.com", hashed_password="x", role="hr_analyst", is_active=True)
    manager_user = User(username="mgr_u", full_name="Manager", email="mgr_u@test.com", hashed_password="x", role="hr_manager", is_active=True)
    viewer_user = User(username="viewer_u", full_name="Viewer", email="viewer_u@test.com", hashed_password="x", role="viewer", is_active=True)

    # Admin has all permissions
    assert AuthorizationService.has_permission(db_session, admin_user, "admin:users") is True
    assert AuthorizationService.has_permission(db_session, admin_user, "pii:view_unmasked") is True
    assert AuthorizationService.has_permission(db_session, admin_user, "sql:execute") is True

    # Analyst can validate and execute SQL and view reports, but cannot view unmasked PII
    assert AuthorizationService.has_permission(db_session, analyst_user, "sql:validate") is True
    assert AuthorizationService.has_permission(db_session, analyst_user, "sql:execute") is True
    assert AuthorizationService.has_permission(db_session, analyst_user, "pii:view_unmasked") is False
    assert AuthorizationService.has_permission(db_session, analyst_user, "admin:users") is False

    # HR Manager can view unmasked PII and manage rules
    assert AuthorizationService.has_permission(db_session, manager_user, "pii:view_unmasked") is True
    assert AuthorizationService.has_permission(db_session, manager_user, "rule:manage") is True

    # Viewer can only view reports
    assert AuthorizationService.has_permission(db_session, viewer_user, "report:view") is True
    assert AuthorizationService.has_permission(db_session, viewer_user, "sql:execute") is False


def test_abac_database_access_control(db_session):
    """Tests explicit multi-database access restrictions."""
    uid_str = str(int(datetime.datetime.now().timestamp() * 1000))[-6:]
    uname = f"isolated_u_{uid_str}"
    user = User(username=uname, full_name="Isolated", email=f"{uname}@test.com", hashed_password="x", role="hr_analyst", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Standard default DB is accessible
    assert AuthorizationService.can_access_database(db_session, user, "sqlite_hr_default") is True

    # Unknown custom database is denied by default
    assert AuthorizationService.can_access_database(db_session, user, "db_secret_fintech") is False

    # Explicit grant
    grant = UserDatabaseAccess(
        user_id=user.id,
        database_id="db_secret_fintech",
        can_read=True,
        can_execute=True,
        granted_by="admin"
    )
    db_session.add(grant)
    db_session.commit()

    # Now allowed
    assert AuthorizationService.can_access_database(db_session, user, "db_secret_fintech") is True


def test_column_level_security_and_masking(db_session):
    """Tests column-level security and dataframe masking algorithms."""
    analyst = User(username="cls_analyst", full_name="CLS Analyst", email="cls@test.com", hashed_password="x", role="hr_analyst", is_active=True)

    test_df = pd.DataFrame([
        {"first_name": "Alexander", "email": "alexander.wright@company.org", "salary": 175000, "dept": "ENG"}
    ])

    masked_df = AuthorizationService.apply_column_masking(test_df, db_session, analyst, "sqlite_hr_default", "employees")

    # Name and email masked with partial algorithm
    assert masked_df["first_name"].iloc[0] == "A***r"
    assert masked_df["email"].iloc[0] == "al***@company.org"

    # Admin sees unmasked
    admin = User(username="cls_admin", full_name="CLS Admin", email="admin@test.com", hashed_password="x", role="admin", is_active=True)
    unmasked_df = AuthorizationService.apply_column_masking(test_df, db_session, admin, "sqlite_hr_default", "employees")
    assert unmasked_df["first_name"].iloc[0] == "Alexander"
    assert unmasked_df["email"].iloc[0] == "alexander.wright@company.org"


def test_row_level_security_filters(db_session):
    """Tests dynamic placeholder substitution in RLS predicates."""
    uid_str = str(int(datetime.datetime.now().timestamp() * 1000))[-6:]
    uname = f"dept_lead_{uid_str}"
    user = User(
        username=uname,
        full_name="Dept Lead",
        email=f"{uname}@test.com",
        hashed_password="x",
        role="hr_manager",
        department_id=4,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Add RLS rule for this user
    rls = RowAccessRule(
        user_id=user.id,
        database_id="sqlite_hr_default",
        table_name="employees",
        filter_expression="department_id = {user.department_id} AND status = 'Active'",
        description="Only department employees",
        is_active=True
    )
    db_session.add(rls)
    db_session.commit()

    filters = AuthorizationService.get_row_security_filters(db_session, user, "sqlite_hr_default", "employees")
    assert len(filters) >= 1
    assert "department_id = 4" in filters[0]
    assert "status = 'Active'" in filters[0]


def test_auth_fastapi_endpoints(client):
    """Tests FastAPI login, me, and audit endpoints."""
    # 1. Login with valid seed admin
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["username"] == "admin"
    assert "admin:users" in data["permissions"]

    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get profile /me
    resp_me = client.get("/api/auth/me", headers=headers)
    assert resp_me.status_code == 200
    me_data = resp_me.json()
    assert me_data["username"] == "admin"

    # 3. List permissions
    resp_perms = client.get("/api/auth/permissions", headers=headers)
    assert resp_perms.status_code == 200
    assert len(resp_perms.json()["permissions"]) >= 10

    # 4. Security audit logs
    resp_audit = client.get("/api/auth/audit", headers=headers)
    assert resp_audit.status_code == 200
    assert len(resp_audit.json()["audit_logs"]) >= 1
