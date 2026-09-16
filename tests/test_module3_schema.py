"""Module 3 Comprehensive Test Suite.

Tests all requirements and acceptance criteria for:
- Deep schema discovery & metadata extraction (tables, views, columns, PKs, FKs, indexes, constraints)
- Zero raw data row querying invariant
- HR semantic mapping (entities, normalized types, metrics vs dimensions, date roles, sensitivity)
- Module 2 SQL repository usage mining & importance scoring
- Schema snapshots, SHA-256 hashing, and drift detection (TABLE_ADDED, COLUMN_REMOVED, TYPE_CHANGED)
- Human metadata editing & verification workflow
- Human edit preservation across schema refreshes
- Manual relationship creation and deletion
- Schema health score calculation
- LlamaIndex-ready RAG schema knowledge generation with sensitive redaction
- FastAPI REST endpoints
"""

import pytest
from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal, init_db
from backend.database.connection_manager import connection_manager
from backend.database.models_schema import (
    SchemaColumn,
    SchemaRelationship,
    SchemaTable,
)
from backend.main import app
from rag.schema_knowledge_builder import SchemaKnowledgeBuilder
from schema.hr_mapping import HRMetadataMapper
from schema.inspector import DeepSchemaInspector
from schema.service import SchemaIntelligenceService
from schema.snapshot import SchemaSnapshotManager
from schema.usage_analyzer import SchemaUsageAnalyzer


@pytest.fixture(scope="module")
def db_session():
    """Provides a database session for tests."""
    init_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def client():
    """Provides a FastAPI TestClient."""
    return TestClient(app)


# -------------------------------------------------------------
# 1. Inspector & Zero Raw Data Invariant
# -------------------------------------------------------------
def test_deep_schema_inspector(db_session):
    """Verifies table, view, column, PK, and FK discovery without raw data rows."""
    engine = connection_manager.get_engine("sqlite_hr_default")
    inspector = DeepSchemaInspector(engine=engine, dialect="sqlite")

    discovery = inspector.inspect_database(database_id="sqlite_hr_default")
    assert discovery["database_id"] == "sqlite_hr_default"
    assert discovery["table_count"] > 0
    assert len(discovery["tables"]) > 0

    # Locate employees table
    emp_tbl = next((t for t in discovery["tables"] if t["table_name"] == "employees"), None)
    assert emp_tbl is not None
    assert emp_tbl["table_type"] == "TABLE"
    assert len(emp_tbl["columns"]) >= 10
    assert "id" in emp_tbl["primary_keys"]

    # Locate foreign keys
    dept_fk = next((fk for fk in emp_tbl["foreign_keys"] if fk["referred_table"] == "departments"), None)
    assert dept_fk is not None
    assert "department_id" in dept_fk["constrained_columns"]

    # Verify no raw data rows are exposed in discovery dict
    for col in emp_tbl["columns"]:
        assert "sample_values" not in col
        assert "rows" not in col
        assert "data" not in col


# -------------------------------------------------------------
# 2. HR Semantic Intelligence Mapping
# -------------------------------------------------------------
def test_hr_semantic_mapping_entities():
    """Verifies entity classification for standard HR tables."""
    assert HRMetadataMapper.classify_table_entity("employees") == "EMPLOYEE"
    assert HRMetadataMapper.classify_table_entity("departments") == "DEPARTMENT"
    assert HRMetadataMapper.classify_table_entity("compensation_history") == "COMPENSATION"
    assert HRMetadataMapper.classify_table_entity("job_profiles") == "JOB_POSITION"
    assert HRMetadataMapper.classify_table_entity("performance_reviews") == "PERFORMANCE"
    assert HRMetadataMapper.classify_table_entity("leave_records") == "LEAVE_ATTENDANCE"
    assert HRMetadataMapper.classify_table_entity("random_audit_table") == "OTHER"


def test_hr_semantic_mapping_attributes():
    """Verifies metric vs dimension, date roles, and sensitivity classifications."""
    # Metric test
    sal_meta = HRMetadataMapper.classify_column_semantics("base_salary", "FLOAT")
    assert sal_meta["is_metric"] is True
    assert sal_meta["is_dimension"] is False
    assert sal_meta["default_aggregation"] == "SUM"
    assert sal_meta["is_sensitive"] is True
    assert sal_meta["sensitive_category"] == "FINANCIAL"

    # Dimension test
    gen_meta = HRMetadataMapper.classify_column_semantics("gender", "VARCHAR(20)")
    assert gen_meta["is_metric"] is False
    assert gen_meta["is_dimension"] is True
    assert gen_meta["is_sensitive"] is False

    # Date Role test
    hire_meta = HRMetadataMapper.classify_column_semantics("hire_date", "DATE")
    assert hire_meta["is_date_field"] is True
    assert hire_meta["date_role"] == "HIRE_DATE"

    term_meta = HRMetadataMapper.classify_column_semantics("termination_date", "DATE")
    assert term_meta["date_role"] == "TERMINATION_DATE"

    # Personal Identifier test
    email_meta = HRMetadataMapper.classify_column_semantics("email", "VARCHAR(100)")
    assert email_meta["is_sensitive"] is True
    assert email_meta["sensitive_category"] == "PERSONAL_IDENTIFIER"


def test_effective_dating_detection():
    """Verifies detection of effective dating patterns."""
    cols_with_eff = ["id", "employee_id", "effective_start_date", "effective_end_date", "is_current"]
    assert HRMetadataMapper.detect_effective_dating(cols_with_eff) is True

    cols_no_eff = ["id", "name", "created_at"]
    assert HRMetadataMapper.detect_effective_dating(cols_no_eff) is False


def test_business_name_generation():
    """Verifies generation of human-readable labels."""
    assert HRMetadataMapper.generate_business_name("compa_ratio") == "Compa-Ratio"
    assert HRMetadataMapper.generate_business_name("employee_number") == "Employee Number"
    assert HRMetadataMapper.generate_business_name("dept_id") == "Department ID"


# -------------------------------------------------------------
# 3. Module 2 SQL Repository Usage Intelligence
# -------------------------------------------------------------
def test_sql_usage_analysis(db_session):
    """Verifies mining of Module 2 SQL queries for table and column frequencies."""
    analyzer = SchemaUsageAnalyzer(db_session)
    usage = analyzer.analyze_repository_usage("sqlite_hr_default")

    assert "table_usage" in usage
    assert "column_usage" in usage
    assert "inferred_joins" in usage
    assert usage["database_id"] == "sqlite_hr_default"

    # Table importance scoring
    score, level = SchemaUsageAnalyzer.calculate_table_importance(
        table_name="employees",
        entity_type="EMPLOYEE",
        column_count=15,
        fk_count=3,
        query_usage_count=5
    )
    assert score >= 70.0
    assert level in ["CRITICAL", "HIGH"]


# -------------------------------------------------------------
# 4. Schema Snapshot & Drift Detection
# -------------------------------------------------------------
def test_schema_snapshot_and_change_detection(db_session):
    """Verifies canonical JSON snapshotting, SHA-256 hashing, and drift detection."""
    snapshot_mgr = SchemaSnapshotManager(db_session)

    old_snap = {
        "database_id": "sqlite_hr_default",
        "table_count": 1,
        "tables": [
            {
                "table_name": "employees",
                "table_type": "TABLE",
                "primary_keys": ["id"],
                "foreign_keys": [],
                "columns": [
                    {"name": "id", "data_type": "INTEGER", "is_primary_key": True, "is_nullable": False},
                    {"name": "name", "data_type": "VARCHAR(50)", "is_primary_key": False, "is_nullable": True},
                    {"name": "old_col", "data_type": "TEXT", "is_primary_key": False, "is_nullable": True},
                ]
            }
        ],
        "relationships": []
    }

    new_snap = {
        "database_id": "sqlite_hr_default",
        "table_count": 2,
        "tables": [
            {
                "table_name": "employees",
                "table_type": "TABLE",
                "primary_keys": ["id"],
                "foreign_keys": [],
                "columns": [
                    {"name": "id", "data_type": "INTEGER", "is_primary_key": True, "is_nullable": False},
                    {"name": "name", "data_type": "VARCHAR(100)", "is_primary_key": False, "is_nullable": True},  # modified type
                    {"name": "new_col", "data_type": "DATE", "is_primary_key": False, "is_nullable": True},  # added
                ]
            },
            {
                "table_name": "departments",  # added table
                "table_type": "TABLE",
                "primary_keys": ["id"],
                "foreign_keys": [],
                "columns": [{"name": "id", "data_type": "INTEGER", "is_primary_key": True, "is_nullable": False}]
            }
        ],
        "relationships": []
    }

    # Verify deterministic hash
    hash1 = SchemaSnapshotManager.compute_schema_hash(old_snap)
    hash2 = SchemaSnapshotManager.compute_schema_hash(old_snap)
    assert hash1 == hash2
    assert len(hash1) == 64

    # Detect changes
    changes = snapshot_mgr.detect_changes(old_snap, new_snap)
    change_types = [c["change_type"] for c in changes]

    assert "TABLE_ADDED" in change_types
    assert "COLUMN_ADDED" in change_types
    assert "COLUMN_REMOVED" in change_types
    assert "COLUMN_TYPE_CHANGED" in change_types


# -------------------------------------------------------------
# 5. Schema Service Full Discovery Flow & Health Score
# -------------------------------------------------------------
def test_schema_service_discovery_and_health(db_session):
    """Verifies end-to-end discovery service, persistence, and health score computation."""
    service = SchemaIntelligenceService(db_session)
    res = service.discover_schema(database_id="sqlite_hr_default")

    assert res["success"] is True
    assert res["tables_discovered"] > 0
    assert res["columns_discovered"] > 0
    assert res["relationships_discovered"] > 0

    # Verify health score
    health = service.get_schema_health("sqlite_hr_default")
    assert health["health_score"] > 0.0
    assert health["table_count"] == res["tables_discovered"]
    assert health["column_count"] == res["columns_discovered"]
    assert health["readiness_status"] in ["EXCELLENT", "GOOD", "FAIR"]


# -------------------------------------------------------------
# 6. Human Metadata Editing & Verification Workflow
# -------------------------------------------------------------
def test_human_metadata_editing_and_verification(db_session):
    """Verifies human editing of business metadata and verification status."""
    service = SchemaIntelligenceService(db_session)

    # Fetch employees table
    emp_table = db_session.query(SchemaTable).filter_by(database_id="sqlite_hr_default", table_name="employees").first()
    assert emp_table is not None

    # Edit table metadata
    updated_tbl = service.update_table_metadata(
        table_id=emp_table.id,
        data={
            "business_name": "Workforce Directory",
            "description": "Master enterprise repository of all employee profiles."
        }
    )
    assert updated_tbl.business_name == "Workforce Directory"

    # Edit column metadata
    col = db_session.query(SchemaColumn).filter_by(table_id=emp_table.id, column_name="base_salary").first()
    if col:
        updated_col = service.update_column_metadata(
            column_id=col.id,
            data={
                "business_definition": "Annualized base cash salary before performance bonuses.",
                "hr_concept": "ANNUAL_BASE_PAY"
            }
        )
        assert updated_col.hr_concept == "ANNUAL_BASE_PAY"

    # Verify table
    verified_tbl = service.verify_table(emp_table.id)
    assert verified_tbl.status == "VERIFIED"
    assert all(c.status == "VERIFIED" for c in verified_tbl.columns)


# -------------------------------------------------------------
# 7. Preservation of Human Metadata Across Refreshes
# -------------------------------------------------------------
def test_preservation_of_human_metadata_on_refresh(db_session):
    """Verifies that schema refresh does NOT wipe out human-authored business metadata or verification status."""
    service = SchemaIntelligenceService(db_session)

    # Set custom business name
    emp_table = db_session.query(SchemaTable).filter_by(database_id="sqlite_hr_default", table_name="employees").first()
    emp_table.business_name = "Preserved Enterprise Personnel Table"
    emp_table.status = "VERIFIED"
    db_session.commit()

    # Trigger schema refresh
    refresh_res = service.refresh_schema("sqlite_hr_default")
    assert refresh_res["success"] is True

    # Re-query
    db_session.expire_all()
    emp_refreshed = db_session.query(SchemaTable).filter_by(database_id="sqlite_hr_default", table_name="employees").first()
    assert emp_refreshed.business_name == "Preserved Enterprise Personnel Table"
    assert emp_refreshed.status == "VERIFIED"


# -------------------------------------------------------------
# 8. Manual Relationship Management
# -------------------------------------------------------------
def test_manual_relationship_management(db_session):
    """Verifies creating, filtering, and deleting manual relationships."""
    service = SchemaIntelligenceService(db_session)

    # Add manual relationship
    rel = service.add_manual_relationship(
        database_id="sqlite_hr_default",
        data={
            "source_table": "employees",
            "source_column": "department_id",
            "target_table": "departments",
            "target_column": "id",
            "relationship_type": "MANY_TO_ONE"
        }
    )
    assert rel.relationship_source == "MANUAL"
    assert rel.is_verified is True

    # List with filter
    manual_rels = service.get_relationships("sqlite_hr_default", source="MANUAL")
    assert any(r["id"] == rel.id for r in manual_rels)

    # Delete
    deleted = service.delete_manual_relationship(rel.id)
    assert deleted is True


# -------------------------------------------------------------
# 9. RAG Schema Knowledge Generation
# -------------------------------------------------------------
def test_rag_schema_knowledge_generation(db_session):
    """Verifies generation of LlamaIndex-ready schema documents and sensitive field redaction."""
    emp_table = db_session.query(SchemaTable).filter_by(database_id="sqlite_hr_default", table_name="employees").first()
    all_rels = db_session.query(SchemaRelationship).filter_by(database_id="sqlite_hr_default").all()

    # Unredacted
    doc_full = SchemaKnowledgeBuilder.build_table_document(
        table=emp_table,
        relationships=all_rels,
        redact_sensitive=False
    )
    assert "HR DATABASE TABLE: EMPLOYEES" in doc_full.text_content
    assert doc_full.metadata["doc_type"] == "schema_table"
    assert doc_full.metadata["has_sensitive_fields"] is True

    # Redacted
    doc_redacted = SchemaKnowledgeBuilder.build_table_document(
        table=emp_table,
        relationships=all_rels,
        redact_sensitive=True
    )
    assert "[REDACTED SENSITIVE FIELD" in doc_redacted.text_content

    # Global catalog
    docs = SchemaKnowledgeBuilder.build_all_documents(db_session, "sqlite_hr_default")
    assert len(docs) >= 2
    assert any(d.doc_type == "schema_catalog" for d in docs)


# -------------------------------------------------------------
# 10. FastAPI REST Endpoints
# -------------------------------------------------------------
def test_fastapi_schema_endpoints(client):
    """Tests all FastAPI schema routes end-to-end."""
    # 1. Health
    res_health = client.get("/api/schema/health?database_id=sqlite_hr_default")
    assert res_health.status_code == 200
    assert res_health.json()["success"] is True
    assert "health_score" in res_health.json()["data"]

    # 2. Tables list
    res_tables = client.get("/api/schema/tables?database_id=sqlite_hr_default")
    assert res_tables.status_code == 200
    tables = res_tables.json()["data"]
    assert len(tables) > 0

    first_tbl_id = tables[0]["id"]

    # 3. Table detail
    res_detail = client.get(f"/api/schema/tables/{first_tbl_id}")
    assert res_detail.status_code == 200
    assert "columns" in res_detail.json()["data"]

    # 4. Search
    res_search = client.get("/api/schema/search?database_id=sqlite_hr_default&q=employee")
    assert res_search.status_code == 200
    assert res_search.json()["success"] is True

    # 5. Relationships
    res_rels = client.get("/api/schema/relationships?database_id=sqlite_hr_default")
    assert res_rels.status_code == 200
    assert isinstance(res_rels.json()["data"], list)

    # 6. Usage
    res_usage = client.get("/api/schema/usage?database_id=sqlite_hr_default")
    assert res_usage.status_code == 200

    # 7. RAG Knowledge
    res_rag = client.get("/api/schema/rag-knowledge?database_id=sqlite_hr_default")
    assert res_rag.status_code == 200
    assert len(res_rag.json()["data"]) > 0
