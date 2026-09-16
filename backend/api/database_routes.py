"""Module 1: Database Connection & Schema Management API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth.dependencies import get_current_user, require_role
from ..database.connection_manager import DatabaseConnectionConfig, connection_manager
from ..database.models import User

router = APIRouter(prefix="/api/database", tags=["Module 1: Database & Schema"])


class TestConnectionRequest(BaseModel):
    db_type: str  # sqlite, postgresql, mysql, sqlserver, oracle
    connection_url: str


class RegisterConnectionRequest(BaseModel):
    database_id: str
    display_name: str
    db_type: str
    connection_url: str
    description: str | None = ""


@router.get("/list")
def list_databases(current_user: User = Depends(get_current_user)):
    """Safe listing of all registered databases without exposing credentials."""
    return connection_manager.list_databases_safe()


@router.post("/test")
def test_database_connection(
    req: TestConnectionRequest,
    current_user: User = Depends(require_role(["admin"]))
):
    """Component 1: Tests connection reachability & auth without persisting credentials."""
    success, message, diagnostics = connection_manager.test_connection(
        db_type=req.db_type,
        connection_url=req.connection_url
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {
        "success": True,
        "message": message,
        "diagnostics": diagnostics
    }


@router.post("/register")
def register_database(
    req: RegisterConnectionRequest,
    current_user: User = Depends(require_role(["admin"]))
):
    """Component 2 & 3: Establishes connection pool and discovers schema metadata."""
    config = DatabaseConnectionConfig(
        database_id=req.database_id,
        display_name=req.display_name,
        db_type=req.db_type,
        connection_url=req.connection_url,
        description=req.description or ""
    )
    schema = connection_manager.register_and_connect(config)
    return {
        "message": f"Database '{req.database_id}' successfully connected and schema discovered.",
        "schema": schema.to_dict()
    }


@router.get("/schema/{database_id}")
def get_database_schema(
    database_id: str,
    current_user: User = Depends(get_current_user)
):
    """Component 3 & 4: Returns structured metadata JSON and schema hash for a database."""
    try:
        schema = connection_manager.get_schema(database_id)
        return schema.to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/dialect/{database_id}")
def get_database_dialect(
    database_id: str,
    current_user: User = Depends(get_current_user)
):
    """Returns dialect rules (date functions, limit syntax) for the target database."""
    rules = connection_manager.get_dialect_rules(database_id)
    return rules.to_dict()
