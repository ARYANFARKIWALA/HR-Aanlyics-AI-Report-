"""Unit and Integration Tests for Module 12 — Reports, Export, Sharing & Report History."""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal, init_db
from backend.database.models import User
from backend.main import app
from reports_lifecycle.execution_service import ReportExecutionService
from reports_lifecycle.export_service import ReportExportService
from reports_lifecycle.report_service import ReportLifecycleService
from reports_lifecycle.schemas import (
    ReportAccessCreateRequest,
    ReportCreateRequest,
    ReportUpdateRequest,
)
from reports_lifecycle.sharing_service import ReportSharingService
from reports_lifecycle.version_service import ReportVersionService


@pytest.fixture(scope="function")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _get_admin_user(db_session) -> User:
    user = db_session.query(User).filter(User.username == "admin").first()
    if not user:
        user = User(
            username="admin",
            full_name="Admin User",
            email="admin@test.com",
            hashed_password="x",
            role="admin",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
    return user


def _create_test_user(db_session, username_prefix: str, role: str = "hr_analyst") -> User:
    uid = uuid.uuid4().hex[:6]
    user = User(
        username=f"{username_prefix}_{uid}",
        full_name=f"Test {username_prefix}",
        email=f"{username_prefix}_{uid}@example.com",
        hashed_password="dummy_hash",
        role=role,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_create_report_and_initial_version(db_session):
    """Test 1: Report creation automatically generates v1 snapshot and owner access rule."""
    admin = _get_admin_user(db_session)
    req = ReportCreateRequest(
        title="Department Headcount Overview",
        description="Active employee count grouped by department",
        category="Headcount",
        database_id="sqlite_hr_default",
        sql_query="SELECT department_id, count(id) as headcount FROM employees GROUP BY department_id;",
        layout_config={"charts": [{"type": "bar", "x": "department_id", "y": "headcount"}]}
    )

    report = ReportLifecycleService.create_report(db=db_session, req=req, user=admin)
    assert report.id is not None
    assert report.report_id.startswith("rep_")
    assert report.title == "Department Headcount Overview"
    assert report.current_version == 1
    assert report.author_username == "admin"
    assert report.is_archived is False
    assert report.is_deleted is False

    # Verify initial version snapshot
    versions = ReportVersionService.list_versions(db=db_session, report=report)
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].change_summary == "Initial creation"

    # Verify owner ACL
    rules = ReportSharingService.list_access_rules(db=db_session, report=report)
    assert len(rules) == 1
    assert rules[0].access_level == "ADMIN"
    assert rules[0].user_id == admin.id


def test_update_report_increments_version_and_creates_snapshot(db_session):
    """Test 2: Report update increments version number and preserves historical snapshot."""
    admin = _get_admin_user(db_session)
    req = ReportCreateRequest(
        title="Initial Comp Analysis",
        sql_query="SELECT id, base_salary FROM employees LIMIT 10;"
    )
    report = ReportLifecycleService.create_report(db=db_session, req=req, user=admin)
    assert report.current_version == 1

    # Update report
    update_req = ReportUpdateRequest(
        title="Updated Comp Analysis",
        sql_query="SELECT id, base_salary, bonus FROM employees LIMIT 20;",
        change_summary="Added bonus column"
    )
    updated = ReportLifecycleService.update_report(
        db=db_session,
        report_id=report.report_id,
        req=update_req,
        user=admin
    )

    assert updated.current_version == 2
    assert updated.title == "Updated Comp Analysis"

    # Verify 2 snapshots exist
    versions = ReportVersionService.list_versions(db=db_session, report=updated)
    assert len(versions) == 2
    assert versions[0].version_number == 2
    assert versions[0].change_summary == "Added bonus column"
    assert versions[1].version_number == 1


def test_non_destructive_restore_version(db_session):
    """Test 3: Restoring an older version creates a NEW version with old contents."""
    admin = _get_admin_user(db_session)
    rep = ReportLifecycleService.create_report(
        db=db_session,
        req=ReportCreateRequest(title="V1 Title", sql_query="SELECT 1;"),
        user=admin
    )

    # Bump to v2
    ReportLifecycleService.update_report(
        db=db_session,
        report_id=rep.report_id,
        req=ReportUpdateRequest(title="V2 Title", sql_query="SELECT 2;"),
        user=admin
    )

    # Bump to v3
    ReportLifecycleService.update_report(
        db=db_session,
        report_id=rep.report_id,
        req=ReportUpdateRequest(title="V3 Title", sql_query="SELECT 3;"),
        user=admin
    )
    assert rep.current_version == 3

    # Restore v1
    restored = ReportVersionService.restore_version(
        db=db_session,
        report=rep,
        version_number=1,
        modifier=admin
    )

    # New version is created (v4) with contents of v1
    assert restored.current_version == 4
    assert restored.title == "V1 Title"
    assert restored.sql_query == "SELECT 1;"

    v_latest = ReportVersionService.get_version(db=db_session, report=restored, version_number=4)
    assert v_latest is not None
    assert "Restored from version 1" in v_latest.change_summary


def test_duplicate_report(db_session):
    """Test 4: Duplicating clones definitions, resets version to 1, and assigns requester as author."""
    user1 = _create_test_user(db_session, "creator")
    user2 = _create_test_user(db_session, "cloner")

    source = ReportLifecycleService.create_report(
        db=db_session,
        req=ReportCreateRequest(
            title="Original Executive Report",
            sql_query="SELECT id, name FROM departments;",
            category="Organization"
        ),
        user=user1
    )

    # User 1 shares report with hr_analyst role
    ReportSharingService.grant_access(
        db=db_session,
        report=source,
        req=ReportAccessCreateRequest(role_name="hr_analyst", access_level="VIEW"),
        granter=user1
    )

    # User 2 duplicates
    dup = ReportLifecycleService.duplicate_report(
        db=db_session,
        report_id=source.report_id,
        user=user2,
        new_title="Cloned Executive Report"
    )

    assert dup.report_id != source.report_id
    assert dup.title == "Cloned Executive Report"
    assert dup.created_by == user2.id
    assert dup.author_username == user2.username
    assert dup.current_version == 1
    assert dup.sql_query == source.sql_query


def test_archive_and_soft_delete(db_session):
    """Test 5: Archiving toggles status and soft-delete marks report deleted."""
    admin = _get_admin_user(db_session)
    report = ReportLifecycleService.create_report(
        db=db_session,
        req=ReportCreateRequest(title="Temporary Report", sql_query="SELECT id FROM departments;"),
        user=admin
    )

    # Archive
    archived = ReportLifecycleService.archive_report(db=db_session, report_id=report.report_id, user=admin, archive=True)
    assert archived.is_archived is True

    # Unarchive
    unarchived = ReportLifecycleService.archive_report(db=db_session, report_id=report.report_id, user=admin, archive=False)
    assert unarchived.is_archived is False

    # Soft-delete
    deleted = ReportLifecycleService.delete_report(db=db_session, report_id=report.report_id, user=admin)
    assert deleted is True

    # Confirm cannot fetch soft-deleted report
    with pytest.raises(KeyError):
        ReportLifecycleService.get_report(db=db_session, report_id=report.report_id, user=admin)


def test_sharing_acl_enforcement(db_session):
    """Test 6: Granular sharing ACL rules (VIEW, EDIT, EXPORT, ADMIN) correctly control access."""
    owner = _create_test_user(db_session, "owner")
    analyst = _create_test_user(db_session, "analyst")

    report = ReportLifecycleService.create_report(
        db=db_session,
        req=ReportCreateRequest(title="Private Department Report", sql_query="SELECT 1;"),
        user=owner
    )

    # 1. Analyst cannot view private report
    with pytest.raises(PermissionError):
        ReportLifecycleService.get_report(db=db_session, report_id=report.report_id, user=analyst)

    # 2. Owner grants VIEW access to Analyst
    ReportSharingService.grant_access(
        db=db_session,
        report=report,
        req=ReportAccessCreateRequest(user_id=analyst.id, access_level="VIEW"),
        granter=owner
    )

    # Now Analyst can view
    rep = ReportLifecycleService.get_report(db=db_session, report_id=report.report_id, user=analyst)
    assert rep.user_access_level == "VIEW"

    # But Analyst cannot edit
    with pytest.raises(PermissionError):
        ReportLifecycleService.update_report(
            db=db_session,
            report_id=report.report_id,
            req=ReportUpdateRequest(title="Hacked Title"),
            user=analyst
        )

    # 3. Upgrade Analyst to EDIT
    ReportSharingService.grant_access(
        db=db_session,
        report=report,
        req=ReportAccessCreateRequest(user_id=analyst.id, access_level="EDIT"),
        granter=owner
    )
    upd = ReportLifecycleService.update_report(
        db=db_session,
        report_id=report.report_id,
        req=ReportUpdateRequest(title="Collaborative Title"),
        user=analyst
    )
    assert upd.title == "Collaborative Title"

    # 4. Revoke access
    rules = ReportSharingService.list_access_rules(db=db_session, report=report)
    analyst_rule = next(r for r in rules if r.user_id == analyst.id)
    ReportSharingService.revoke_access(db=db_session, report=report, access_id=analyst_rule.id)

    # Denied again
    with pytest.raises(PermissionError):
        ReportLifecycleService.get_report(db=db_session, report_id=report.report_id, user=analyst)


def test_re_run_revalidation_invariant(db_session):
    """Test 7: Re-running a report forces Module 7 validation + Module 8 execution and audit log."""
    admin = _get_admin_user(db_session)
    report = ReportLifecycleService.create_report(
        db=db_session,
        req=ReportCreateRequest(
            title="Departments Directory",
            sql_query="SELECT id, name, code, budget FROM departments ORDER BY id ASC;"
        ),
        user=admin
    )

    # Run report
    res = ReportExecutionService.run_report(db=db_session, report=report, user=admin)
    assert res.status == "SUCCESS"
    assert res.row_count > 0
    assert "name" in res.columns
    assert res.validation_id.startswith("val_")
    assert res.execution_id.startswith("exec_")

    # Verify execution history recorded
    history = ReportExecutionService.list_executions(db=db_session, report=report)
    assert len(history) == 1
    assert history[0].validation_id == res.validation_id
    assert history[0].status == "SUCCESS"
    assert history[0].row_count == res.row_count

    # Test dangerous SQL rejection during re-run
    # Directly update report sql to bypass UI
    report.sql_query = "DROP TABLE departments; SELECT 1;"
    db_session.commit()

    blocked_res = ReportExecutionService.run_report(db=db_session, report=report, user=admin)
    assert blocked_res.status == "VALIDATION_FAILED"
    assert blocked_res.row_count == 0
    assert "Validation failed" in blocked_res.error


def test_export_formats_and_cls_masking(db_session):
    """Test 8: CSV, Excel, and PDF exports are generated cleanly with PII masking."""
    admin = _get_admin_user(db_session)
    analyst = _create_test_user(db_session, "analyst_viewer", role="hr_analyst")

    report = ReportLifecycleService.create_report(
        db=db_session,
        req=ReportCreateRequest(
            title="Compensation & Contact Export",
            sql_query="SELECT first_name, last_name, email, base_salary FROM employees LIMIT 5;"
        ),
        user=admin
    )

    cols = ["first_name", "last_name", "email", "base_salary"]
    rows = [
        {"first_name": "Alice", "last_name": "Smith", "email": "alice.smith@company.com", "base_salary": 125000.0},
        {"first_name": "Bob", "last_name": "Jones", "email": "bob.jones@company.com", "base_salary": 98000.0},
    ]

    # 1. Test CSV Export with masking for analyst
    csv_bytes = ReportExportService.export_csv(report=report, columns=cols, rows=rows, user=analyst)
    csv_str = csv_bytes.decode("utf-8")
    assert "first_name" in csv_str
    # Email should be masked
    assert "***" in csv_str

    # 2. Test Excel Export
    excel_bytes = ReportExportService.export_excel(report=report, columns=cols, rows=rows, user=analyst)
    assert len(excel_bytes) > 1000
    assert excel_bytes.startswith(b"PK")  # Zip/XLSX header

    # 3. Test PDF Export
    pdf_bytes = ReportExportService.export_pdf(report=report, columns=cols, rows=rows, user=analyst)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def test_fastapi_report_lifecycle_endpoints(client, db_session):
    """Test 9: FastAPI endpoints for reports lifecycle, versions, sharing, running, and export."""
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Report
    create_resp = client.post(
        "/api/reports-lifecycle",
        headers=headers,
        json={
            "title": "API Lifecycle Test Report",
            "description": "Integration test report",
            "category": "Testing",
            "sql_query": "SELECT id, name FROM departments;"
        }
    )
    assert create_resp.status_code == 201
    rep_data = create_resp.json()
    rep_id = rep_data["report_id"]
    assert rep_data["current_version"] == 1

    # 2. Get Report
    get_resp = client.get(f"/api/reports-lifecycle/{rep_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "API Lifecycle Test Report"

    # 3. Update Report
    upd_resp = client.put(
        f"/api/reports-lifecycle/{rep_id}",
        headers=headers,
        json={"title": "Updated API Title", "change_summary": "Renamed for test"}
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["current_version"] == 2

    # 4. List Versions
    ver_resp = client.get(f"/api/reports-lifecycle/{rep_id}/versions", headers=headers)
    assert ver_resp.status_code == 200
    assert len(ver_resp.json()) == 2

    # 5. Restore v1
    restore_resp = client.post(f"/api/reports-lifecycle/{rep_id}/versions/1/restore", headers=headers)
    assert restore_resp.status_code == 200
    assert restore_resp.json()["current_version"] == 3
    assert restore_resp.json()["title"] == "API Lifecycle Test Report"

    # 6. Run Report
    run_resp = client.post(f"/api/reports-lifecycle/{rep_id}/run", headers=headers)
    assert run_resp.status_code == 200
    assert run_resp.json()["status"] == "SUCCESS"
    assert run_resp.json()["row_count"] > 0

    # 7. Check Executions
    exec_resp = client.get(f"/api/reports-lifecycle/{rep_id}/executions", headers=headers)
    assert exec_resp.status_code == 200
    assert len(exec_resp.json()) >= 1

    # 8. Export CSV
    csv_resp = client.post(f"/api/reports-lifecycle/{rep_id}/export/csv", headers=headers)
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    assert len(csv_resp.content) > 0

    # 9. Duplicate Report
    dup_resp = client.post(
        f"/api/reports-lifecycle/{rep_id}/duplicate",
        headers=headers,
        json={"new_title": "Duplicated API Report"}
    )
    assert dup_resp.status_code == 200
    assert dup_resp.json()["title"] == "Duplicated API Report"
