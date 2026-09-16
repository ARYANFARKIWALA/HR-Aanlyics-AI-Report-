"""Module 3: HR Database Schema & Business Metadata Intelligence API Endpoints.

Implements all discovery, refresh, health monitoring, human metadata editing,
verification workflows, relationship graphs, drift auditing, and RAG knowledge generation.
Standard JSON envelopes:
  Success: { "success": true, "data": { ... } }
  Error:   { "success": false, "error": { "code": "...", "message": "..." } }
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from rag.schema_knowledge_builder import SchemaKnowledgeBuilder
from schema.service import SchemaIntelligenceService

from ..auth.dependencies import get_current_user
from ..database.connection import get_db
from ..database.models import User

router = APIRouter(prefix="/api/schema", tags=["Module 3: Schema & Business Metadata Intelligence"])


# -------------------------------------------------------------
# Request & Response Models
# -------------------------------------------------------------
class DiscoverSchemaRequest(BaseModel):
    database_id: str = Field(..., min_length=1, description="Database connection identifier")


class TableUpdateMetadataRequest(BaseModel):
    business_name: str | None = None
    description: str | None = None
    business_entity: str | None = None
    status: str | None = None


class ColumnUpdateMetadataRequest(BaseModel):
    business_name: str | None = None
    description: str | None = None
    business_definition: str | None = None
    hr_concept: str | None = None
    is_sensitive: bool | None = None
    sensitive_category: str | None = None
    is_date_field: bool | None = None
    date_role: str | None = None
    is_metric: bool | None = None
    default_aggregation: str | None = None
    is_dimension: bool | None = None
    status: str | None = None


class ManualRelationshipRequest(BaseModel):
    database_id: str
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relationship_type: str | None = "MANY_TO_ONE"


def success_response(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}


def error_response(code: str, message: str, status_code: int = 400):
    raise HTTPException(
        status_code=status_code,
        detail={"success": False, "error": {"code": code, "message": message}}
    )


# -------------------------------------------------------------
# 1. Discovery & Refresh
# -------------------------------------------------------------
@router.post("/discover")
def trigger_discovery(
    request: DiscoverSchemaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Triggers deep schema discovery and semantic HR metadata mapping."""
    try:
        service = SchemaIntelligenceService(db)
        result = service.discover_schema(database_id=request.database_id, user_id=current_user.id)
        return success_response(result)
    except ValueError as e:
        error_response("DISCOVERY_FAILED", str(e), status_code=400)
    except Exception as e:
        error_response("INTERNAL_ERROR", f"Schema discovery failed: {e!s}", status_code=500)


@router.post("/refresh")
def trigger_refresh(
    request: DiscoverSchemaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refreshes schema, detects drift/changes, and preserves human metadata."""
    try:
        service = SchemaIntelligenceService(db)
        result = service.refresh_schema(database_id=request.database_id, user_id=current_user.id)
        return success_response(result)
    except ValueError as e:
        error_response("REFRESH_FAILED", str(e), status_code=400)
    except Exception as e:
        error_response("INTERNAL_ERROR", f"Schema refresh failed: {e!s}", status_code=500)


# -------------------------------------------------------------
# 2. Schema Health & Overview
# -------------------------------------------------------------
@router.get("/health")
def get_schema_health(
    database_id: str = Query("sqlite_hr_default"),
    db: Session = Depends(get_db)
):
    """Calculates schema completeness and AI readiness score."""
    service = SchemaIntelligenceService(db)
    health = service.get_schema_health(database_id=database_id)
    return success_response(health)


# -------------------------------------------------------------
# 3. Tables & Views
# -------------------------------------------------------------
@router.get("/tables")
def list_tables(
    database_id: str = Query("sqlite_hr_default"),
    entity_type: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """Lists discovered tables with importance levels, entity classifications, and verification status."""
    service = SchemaIntelligenceService(db)
    tables = service.get_tables(
        database_id=database_id,
        entity_type=entity_type,
        status=status,
        search=search
    )
    return success_response(tables)


@router.get("/tables/{table_id}")
def get_table_details(
    table_id: int,
    db: Session = Depends(get_db)
):
    """Returns granular details for a table including columns, relationships, and usage."""
    service = SchemaIntelligenceService(db)
    detail = service.get_table_detail(table_id=table_id)
    if not detail:
        error_response("TABLE_NOT_FOUND", f"Schema table ID {table_id} not found", status_code=404)
    return success_response(detail)


@router.put("/tables/{table_id}")
def update_table_metadata(
    table_id: int,
    request: TableUpdateMetadataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enables human business metadata editing on a table."""
    service = SchemaIntelligenceService(db)
    updated = service.update_table_metadata(
        table_id=table_id,
        data=request.dict(exclude_unset=True),
        user_id=current_user.id
    )
    if not updated:
        error_response("TABLE_NOT_FOUND", f"Schema table ID {table_id} not found", status_code=404)
    return success_response({
        "id": updated.id,
        "table_name": updated.table_name,
        "business_name": updated.business_name,
        "business_entity": updated.business_entity,
        "status": updated.status,
        "description": updated.description
    })


@router.post("/tables/{table_id}/verify")
def verify_table(
    table_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marks a table and its columns as human-verified."""
    service = SchemaIntelligenceService(db)
    verified = service.verify_table(table_id=table_id, user_id=current_user.id)
    if not verified:
        error_response("TABLE_NOT_FOUND", f"Schema table ID {table_id} not found", status_code=404)
    return success_response({
        "id": verified.id,
        "table_name": verified.table_name,
        "status": verified.status,
        "verified_at": verified.verified_at.isoformat() if verified.verified_at else None
    })


# -------------------------------------------------------------
# 4. Columns Metadata Governance
# -------------------------------------------------------------
@router.put("/columns/{column_id}")
def update_column_metadata(
    column_id: int,
    request: ColumnUpdateMetadataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enables human business definition, sensitivity, and metric classification on a column."""
    service = SchemaIntelligenceService(db)
    updated = service.update_column_metadata(
        column_id=column_id,
        data=request.dict(exclude_unset=True),
        user_id=current_user.id
    )
    if not updated:
        error_response("COLUMN_NOT_FOUND", f"Schema column ID {column_id} not found", status_code=404)
    return success_response({
        "id": updated.id,
        "column_name": updated.column_name,
        "business_name": updated.business_name,
        "business_definition": updated.business_definition,
        "hr_concept": updated.hr_concept,
        "is_sensitive": updated.is_sensitive,
        "sensitive_category": updated.sensitive_category,
        "is_metric": updated.is_metric,
        "status": updated.status
    })


@router.post("/columns/{column_id}/verify")
def verify_column(
    column_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marks an individual column as human-verified."""
    service = SchemaIntelligenceService(db)
    verified = service.verify_column(column_id=column_id, user_id=current_user.id)
    if not verified:
        error_response("COLUMN_NOT_FOUND", f"Schema column ID {column_id} not found", status_code=404)
    return success_response({
        "id": verified.id,
        "column_name": verified.column_name,
        "status": verified.status
    })


# -------------------------------------------------------------
# 5. Relationships & Joins
# -------------------------------------------------------------
@router.get("/relationships")
def list_relationships(
    database_id: str = Query("sqlite_hr_default"),
    source: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """Lists relationships across database tables (Foreign Keys, SQL Usage, Manual)."""
    service = SchemaIntelligenceService(db)
    rels = service.get_relationships(database_id=database_id, source=source)
    return success_response(rels)


@router.post("/relationships")
def create_manual_relationship(
    request: ManualRelationshipRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Defines a manual relationship link between two tables."""
    try:
        service = SchemaIntelligenceService(db)
        rel = service.add_manual_relationship(
            database_id=request.database_id,
            data=request.dict(),
            user_id=current_user.id
        )
        return success_response({
            "id": rel.id,
            "source_table": rel.source_table_name,
            "source_column": rel.source_column_name,
            "target_table": rel.target_table_name,
            "target_column": rel.target_column_name,
            "relationship_source": rel.relationship_source,
            "is_verified": rel.is_verified
        })
    except ValueError as e:
        error_response("INVALID_RELATIONSHIP", str(e), status_code=400)


@router.delete("/relationships/{relationship_id}")
def delete_manual_relationship(
    relationship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Removes a manually created relationship."""
    service = SchemaIntelligenceService(db)
    deleted = service.delete_manual_relationship(relationship_id=relationship_id)
    if not deleted:
        error_response("RELATIONSHIP_NOT_FOUND", f"Manual relationship ID {relationship_id} not found", status_code=404)
    return success_response({"deleted": True, "id": relationship_id})


# -------------------------------------------------------------
# 6. Drift, Snapshots, Usage & Search
# -------------------------------------------------------------
@router.get("/changes")
def get_schema_changes(
    database_id: str = Query("sqlite_hr_default"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Returns detected schema drift and modifications."""
    service = SchemaIntelligenceService(db)
    changes = service.get_schema_changes(database_id=database_id, limit=limit)
    return success_response(changes)


@router.get("/snapshots")
def list_snapshots(
    database_id: str = Query("sqlite_hr_default"),
    db: Session = Depends(get_db)
):
    """Lists historical snapshots for a database."""
    service = SchemaIntelligenceService(db)
    snapshots = service.get_snapshots(database_id=database_id)
    return success_response(snapshots)


@router.get("/usage")
def get_usage_statistics(
    database_id: str = Query("sqlite_hr_default"),
    db: Session = Depends(get_db)
):
    """Returns table, column, and join query frequencies mined from Module 2."""
    service = SchemaIntelligenceService(db)
    usage = service.get_usage_metrics(database_id=database_id)
    return success_response(usage)


@router.get("/search")
def search_schema(
    database_id: str = Query("sqlite_hr_default"),
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """Searches schema entities and columns by keywords."""
    service = SchemaIntelligenceService(db)
    results = service.search_schema(database_id=database_id, query_term=q)
    return success_response(results)


# -------------------------------------------------------------
# 7. RAG Knowledge Generation
# -------------------------------------------------------------
@router.get("/rag-knowledge")
def get_rag_knowledge_documents(
    database_id: str = Query("sqlite_hr_default"),
    redact_sensitive: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Generates LlamaIndex-ready structured documents for RAG indexing."""
    docs = SchemaKnowledgeBuilder.build_all_documents(
        db=db,
        database_id=database_id,
        redact_sensitive=redact_sensitive
    )
    return success_response([d.to_dict() for d in docs])
