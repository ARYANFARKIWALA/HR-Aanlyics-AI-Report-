"""Module 2 Test Suite: Existing SQL Repository & SQL Knowledge Management.

Comprehensive unit and integration tests covering:
1. Add valid SQL
2. Add empty SQL
3. Add invalid SQL
4. Upload valid SQL file
5. Upload invalid SQL file
6. Bulk import
7. Detect duplicate SQL
8. Extract tables
9. Extract columns
10. Extract joins
11. Extract aggregations
12. Detect date logic
13. Detect effective dating
14. Detect security filters
15. Create version
16. Compare versions
17. Approve report
18. Reject report
19. Archive report
20. Role-based unauthorized access
21. RAG knowledge document builder
"""

import pytest
from backend.database.connection import SessionLocal, init_db
from backend.database.models import User
from backend.database.models_repo import SQLReport, SQLReportVersion, SQLApproval
from backend.services.sql_repository_service import SQLRepositoryService
from sql.normalizer import SQLNormalizer
from sql.file_parser import SQLFileParser
from sql.parser import SQLParser
from rag.sql_knowledge_builder import SQLKnowledgeBuilder


@pytest.fixture
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def admin_user(db_session):
    user = db_session.query(User).filter_by(username="admin").first()
    if not user:
        user = User(username="admin", email="admin@test.local", hashed_password="pwd", full_name="Admin", role="admin")
        db_session.add(user)
        db_session.commit()
    return user


@pytest.fixture
def viewer_user(db_session):
    user = db_session.query(User).filter_by(username="viewer_test").first()
    if not user:
        user = User(username="viewer_test", email="viewer@test.local", hashed_password="pwd", full_name="Viewer", role="viewer")
        db_session.add(user)
        db_session.commit()
    return user


# 1. Add Valid SQL
def test_add_valid_sql(db_session, admin_user):
    sql = "SELECT department_id, COUNT(id) AS cnt FROM employees GROUP BY department_id;"
    report, dup_info = SQLRepositoryService.create_report(
        session=db_session,
        report_name="Valid Test Report",
        sql_query=sql,
        database_id="sqlite_hr_default",
        user=admin_user,
        category="Headcount"
    )
    assert report.id is not None
    assert report.report_code.startswith("SQLRPT-")
    assert report.is_valid is True
    assert report.status == "PENDING_REVIEW"
    assert report.version == 1


# 2. Add Empty SQL
def test_add_empty_sql(db_session, admin_user):
    meta = SQLParser.parse_query("")
    assert meta.is_valid is False
    assert "empty" in meta.validation_error.lower()


# 3. Add Invalid SQL
def test_add_invalid_sql(db_session, admin_user):
    bad_sql = "SELECT FROM WHERE GROUP BY ORDER;"
    report, _ = SQLRepositoryService.create_report(
        session=db_session,
        report_name="Invalid SQL Report",
        sql_query=bad_sql,
        database_id="sqlite_hr_default",
        user=admin_user,
        category="Other"
    )
    assert report.is_valid is False
    assert report.status == "INVALID"
    assert report.validation_error is not None


# 4. Upload Valid SQL File
def test_upload_valid_sql_file(db_session, admin_user):
    file_content = """-- Report Name: Turnover Analysis
-- Description: Measures turnover
-- Category: Attrition
SELECT name, turnover_rate FROM departments;"""
    entries = SQLFileParser.parse_content(file_content, filename="turnover.sql")
    assert len(entries) == 1
    assert entries[0].extracted_name == "Turnover Analysis"
    assert entries[0].extracted_category == "Attrition"


# 5. Upload Invalid SQL File
def test_upload_invalid_sql_file(db_session, admin_user):
    file_content = "NOT A VALID SQL STATEMENT AT ALL !!;"
    entries = SQLFileParser.parse_content(file_content, filename="broken.sql")
    assert len(entries) == 1
    meta = SQLParser.parse_query(entries[0].raw_sql)
    assert meta.is_valid is False


import uuid

# 6. Bulk Import
def test_bulk_import(db_session, admin_user):
    token = uuid.uuid4().hex[:8]
    files = {
        f"file1_{token}.sql": f"SELECT id, name AS dept_{token} FROM departments;",
        f"file2_{token}.sql": f"SELECT id, first_name AS emp_{token} FROM employees;"
    }
    summary = SQLRepositoryService.bulk_import(
        session=db_session,
        files_dict=files,
        database_id="sqlite_hr_default",
        user=admin_user
    )
    assert summary["total_files"] == 2
    assert summary["imported_valid"] >= 2


# 7. Detect Duplicate SQL
def test_detect_duplicate_sql(db_session, admin_user):
    token = uuid.uuid4().hex[:8]
    sql1 = f"SELECT first_name, email AS col_{token} FROM employees WHERE status = 'Active';"
    sql2 = f"""select  first_name,
                     email as col_{token}
              from    employees
              where   status = 'Active';"""

    # Equivalence check
    assert SQLNormalizer.are_structurally_equivalent(sql1, sql2) is True

    # Ingest first
    rep1, dup1 = SQLRepositoryService.create_report(
        session=db_session,
        report_name=f"Original Active Staff {token}",
        sql_query=sql1,
        database_id="sqlite_hr_default",
        user=admin_user
    )
    assert dup1["is_duplicate"] is False

    # Ingest second
    rep2, dup2 = SQLRepositoryService.create_report(
        session=db_session,
        report_name=f"Duplicate Active Staff {token}",
        sql_query=sql2,
        database_id="sqlite_hr_default",
        user=admin_user
    )
    assert dup2["is_duplicate"] is True
    assert dup2["duplicate_report_code"] == rep1.report_code


# 8. Extract Tables
def test_extract_tables():
    sql = "SELECT e.id, d.name FROM employees e JOIN departments d ON e.department_id = d.id;"
    meta = SQLParser.parse_query(sql)
    assert "employees" in meta.tables
    assert "departments" in meta.tables


# 9. Extract Columns
def test_extract_columns():
    sql = "SELECT e.first_name, e.last_name, d.name AS dept_name FROM employees e JOIN departments d ON e.department_id = d.id;"
    meta = SQLParser.parse_query(sql)
    assert "first_name" in meta.columns
    assert "last_name" in meta.columns
    assert "dept_name" in meta.columns


# 10. Extract Joins
def test_extract_joins():
    sql = "SELECT * FROM employees e LEFT JOIN departments d ON e.department_id = d.id;"
    meta = SQLParser.parse_query(sql)
    assert len(meta.joins) == 1
    assert "LEFT" in meta.joins[0]["join_type"]
    assert meta.joins[0]["right_table"] == "departments"


# 11. Extract Aggregations
def test_extract_aggregations():
    sql = "SELECT department_id, COUNT(id), AVG(salary), SUM(bonus) FROM employees GROUP BY department_id;"
    meta = SQLParser.parse_query(sql)
    funcs = [a["function"] for a in meta.aggregations]
    assert "COUNT" in funcs
    assert "AVG" in funcs
    assert "SUM" in funcs


# 12. Detect Date Logic
def test_detect_date_logic():
    sql = "SELECT * FROM employees WHERE hire_date >= '2024-01-01' AND termination_date IS NULL;"
    meta = SQLParser.parse_query(sql)
    assert len(meta.date_conditions) >= 2


# 13. Detect Effective Dating
def test_detect_effective_dating():
    sql = "SELECT * FROM employees WHERE effective_start_date <= CURRENT_DATE AND effective_end_date >= CURRENT_DATE AND is_current = 1;"
    meta = SQLParser.parse_query(sql)
    assert meta.uses_effective_dating is True


# 14. Detect Security Filters
def test_detect_security_filters():
    sql = "SELECT * FROM employees WHERE company_id = :company_id AND department_id = :dept_id;"
    meta = SQLParser.parse_query(sql)
    assert meta.uses_security_filter is True
    assert "company_id" in meta.security_filters_details
    assert "department_id" in meta.security_filters_details


# 15. Create Version
def test_create_version(db_session, admin_user):
    initial_sql = "SELECT id, first_name FROM employees;"
    report, _ = SQLRepositoryService.create_report(
        session=db_session,
        report_name="Versionable Report",
        sql_query=initial_sql,
        database_id="sqlite_hr_default",
        user=admin_user
    )
    assert report.version == 1

    # Update SQL
    new_sql = "SELECT id, first_name, last_name, email FROM employees;"
    updated = SQLRepositoryService.update_report(
        session=db_session,
        report_id=report.id,
        user=admin_user,
        sql_query=new_sql,
        change_description="Added last_name and email columns."
    )
    assert updated.version == 2
    assert len(updated.versions) == 2


# 16. Compare Versions
def test_compare_versions(db_session, admin_user):
    rep = db_session.query(SQLReport).filter_by(report_name="Versionable Report").first()
    diff_res = SQLRepositoryService.compare_versions(db_session, rep.id, 1, 2)
    assert diff_res["version_1"] == 1
    assert diff_res["version_2"] == 2
    assert "last_name" in diff_res["diff_text"]


# 17. Approve Report
def test_approve_report(db_session, admin_user):
    report, _ = SQLRepositoryService.create_report(
        session=db_session,
        report_name="Approvable Report",
        sql_query="SELECT id, name FROM departments;",
        database_id="sqlite_hr_default",
        user=admin_user
    )
    assert report.status == "PENDING_REVIEW"

    approved = SQLRepositoryService.approve_report(db_session, report.id, admin_user, comment="Verified.")
    assert approved.status == "APPROVED"
    assert len(approved.approvals) == 1
    assert approved.approvals[0].action == "APPROVE"


# 18. Reject Report
def test_reject_report(db_session, admin_user):
    report, _ = SQLRepositoryService.create_report(
        session=db_session,
        report_name="Rejectable Report",
        sql_query="SELECT id FROM departments;",
        database_id="sqlite_hr_default",
        user=admin_user
    )
    rejected = SQLRepositoryService.reject_report(db_session, report.id, admin_user, reason="Needs department name.")
    assert rejected.status == "REJECTED"


# 19. Archive Report
def test_archive_report(db_session, admin_user):
    report, _ = SQLRepositoryService.create_report(
        session=db_session,
        report_name="Archivable Report",
        sql_query="SELECT id FROM departments;",
        database_id="sqlite_hr_default",
        user=admin_user
    )
    archived = SQLRepositoryService.archive_report(db_session, report.id, admin_user, reason="Legacy.")
    assert archived.status == "ARCHIVED"


# 20. Role-based Permission Test
def test_unauthorized_viewer_access(db_session, viewer_user):
    # Viewer role cannot approve
    from backend.auth.dependencies import require_role
    checker = require_role(["admin", "hr_manager"])
    with pytest.raises(Exception):
        checker(viewer_user)


# 21. RAG Knowledge Document Builder
def test_rag_knowledge_document_builder(db_session, admin_user):
    rep = db_session.query(SQLReport).filter_by(status="APPROVED").first()
    assert rep is not None
    doc = SQLKnowledgeBuilder.build_knowledge_document(rep, rep.metadata_rel)
    assert doc.doc_id.startswith("KNOW-")
    assert rep.report_name in doc.text_content
    assert "Verified Enterprise SQL Query" in doc.text_content
    assert doc.metadata["status"] == "APPROVED"
    assert "organization_id" in doc.metadata
