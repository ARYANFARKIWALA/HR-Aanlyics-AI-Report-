"""Comprehensive Unit and Integration Tests for Phase 12 — Authentication & RBAC."""

import pytest
from fastapi import HTTPException

from backend.auth.authorization import AuthorizationService
from backend.auth.password import PasswordManager
from backend.auth.sessions import SessionManager
from backend.database.connection import SessionLocal, init_db
from backend.database.models import User


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_rbac_canonical_roles_permissions(db_session):
    """
    Test the 5 canonical roles:
    SUPER_ADMIN, HR_ADMIN, HR_MANAGER, ANALYST, REPORT_VIEWER.
    """
    # 1. SUPER_ADMIN
    super_admin = User(username="super_admin_test", role="SUPER_ADMIN", is_active=True)
    assert AuthorizationService.has_permission(db_session, super_admin, "admin:manage") is True
    assert AuthorizationService.has_permission(db_session, super_admin, "db:select") is True
    assert AuthorizationService.has_permission(db_session, super_admin, "sensitive:access") is True

    # 2. HR_ADMIN
    hr_admin = User(username="hr_admin_test", role="HR_ADMIN", is_active=True)
    assert AuthorizationService.has_permission(db_session, hr_admin, "admin:manage") is True
    assert AuthorizationService.has_permission(db_session, hr_admin, "sql:upload") is True
    assert AuthorizationService.has_permission(db_session, hr_admin, "rule:edit") is True
    assert AuthorizationService.has_permission(db_session, hr_admin, "rag:manage") is True

    # 3. HR_MANAGER
    hr_manager = User(username="hr_manager_test", role="HR_MANAGER", is_active=True)
    assert AuthorizationService.has_permission(db_session, hr_manager, "db:select") is True
    assert AuthorizationService.has_permission(db_session, hr_manager, "schema:access") is True
    assert AuthorizationService.has_permission(db_session, hr_manager, "rule:edit") is True
    assert AuthorizationService.has_permission(db_session, hr_manager, "report:create") is True
    assert AuthorizationService.has_permission(db_session, hr_manager, "report:execute") is True
    assert AuthorizationService.has_permission(db_session, hr_manager, "sensitive:access") is True
    assert AuthorizationService.has_permission(db_session, hr_manager, "admin:manage") is False

    # 4. ANALYST
    analyst = User(username="analyst_test", role="ANALYST", is_active=True)
    assert AuthorizationService.has_permission(db_session, analyst, "db:select") is True
    assert AuthorizationService.has_permission(db_session, analyst, "schema:access") is True
    assert AuthorizationService.has_permission(db_session, analyst, "report:create") is True
    assert AuthorizationService.has_permission(db_session, analyst, "report:execute") is True
    assert AuthorizationService.has_permission(db_session, analyst, "sensitive:access") is False
    assert AuthorizationService.has_permission(db_session, analyst, "admin:manage") is False

    # 5. REPORT_VIEWER
    viewer = User(username="viewer_test", role="REPORT_VIEWER", is_active=True)
    assert AuthorizationService.has_permission(db_session, viewer, "report:view") is True
    assert AuthorizationService.has_permission(db_session, viewer, "report:execute") is True
    assert AuthorizationService.has_permission(db_session, viewer, "report:create") is False
    assert AuthorizationService.has_permission(db_session, viewer, "rule:edit") is False
    assert AuthorizationService.has_permission(db_session, viewer, "sensitive:access") is False
    assert AuthorizationService.has_permission(db_session, viewer, "admin:manage") is False


def test_password_security_and_pbkdf2():
    """Verify PBKDF2 hashing, salt generation, and validation."""
    pwd = "SecureHRPassword!2026"
    hashed = PasswordManager.hash_password(pwd)

    assert hashed != pwd
    assert PasswordManager.verify_password(pwd, hashed) is True
    assert PasswordManager.verify_password("WrongPassword123", hashed) is False


def test_account_lockout_policy(db_session):
    """Test locking account after 5 failed login attempts."""
    import uuid
    uname = f"lockout_{uuid.uuid4().hex[:8]}"
    user = User(
        username=uname,
        email=f"{uname}@example.com",
        hashed_password=PasswordManager.hash_password("Pass123!"),
        full_name="Lockout Test",
        role="ANALYST",
        is_active=True,
        failed_login_attempts=0
    )
    db_session.add(user)
    db_session.commit()

    # Simulate 5 failed attempts
    for i in range(5):
        SessionManager.record_login_failure(db_session, user)

    assert user.failed_login_attempts == 5
    is_locked, _ = SessionManager.is_account_locked(user)
    assert is_locked is True


def test_backend_permission_dependencies(db_session):
    """Verify that require_permission dependency raises HTTP 403 for unauthorized users."""
    from backend.auth.dependencies import require_permission

    viewer = User(username="viewer_dep_test", role="REPORT_VIEWER", is_active=True)
    checker = require_permission("admin:manage")

    with pytest.raises(HTTPException) as exc_info:
        checker(current_user=viewer, db=db_session)

    assert exc_info.value.status_code == 403
    assert "Missing required capability" in exc_info.value.detail
