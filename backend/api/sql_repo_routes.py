"""Enterprise SQL Knowledge Repository API routes."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database.connection import get_db
from ..database.models import SQLRepository, User
from ..auth.dependencies import get_current_user, require_role
from rag.retrieval import rag_retriever

router = APIRouter(prefix="/api/sql-repo", tags=["SQL Knowledge Repository"])


class SQLTemplateCreateRequest(BaseModel):
    report_title: str
    category: str
    business_description: str
    raw_sql: str
    business_rules_explained: str
    joins_explained: str
    effective_dating_explained: str
    tags: str = ""


class SQLSearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.get("/")
def list_sql_templates(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lists all verified enterprise SQL report templates in the repository."""
    q = db.query(SQLRepository)
    if category:
        q = q.filter(SQLRepository.category == category)
    templates = q.order_by(SQLRepository.report_title).all()
    return [
        {
            "id": t.id,
            "report_title": t.report_title,
            "category": t.category,
            "business_description": t.business_description,
            "raw_sql": t.raw_sql,
            "business_rules_explained": t.business_rules_explained,
            "joins_explained": t.joins_explained,
            "effective_dating_explained": t.effective_dating_explained,
            "tags": t.tags,
            "author": t.author,
            "created_at": t.created_at.isoformat() if t.created_at else ""
        }
        for t in templates
    ]


@router.get("/{template_id}")
def get_sql_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Retrieves single enterprise template details."""
    template = db.query(SQLRepository).filter(SQLRepository.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="SQL Template not found")
    return {
        "id": template.id,
        "report_title": template.report_title,
        "category": template.category,
        "business_description": template.business_description,
        "raw_sql": template.raw_sql,
        "business_rules_explained": template.business_rules_explained,
        "joins_explained": template.joins_explained,
        "effective_dating_explained": template.effective_dating_explained,
        "tags": template.tags,
        "author": template.author
    }


@router.post("/search")
def search_sql_repository(
    req: SQLSearchRequest,
    db: Session = Depends(get_db)
):
    """Performs semantic vector search across existing verified SQL templates."""
    if not rag_retriever._initialized:
        rag_retriever.initialize(db)
    
    matches = rag_retriever.search_sql_templates(req.query, top_k=req.top_k)
    return {
        "query": req.query,
        "matches": matches
    }


@router.post("/")
def create_sql_template(
    req: SQLTemplateCreateRequest,
    current_user: User = Depends(require_role(["admin", "hr_manager"])),
    db: Session = Depends(get_db)
):
    """Adds a new verified enterprise SQL template to the organization catalog."""
    new_template = SQLRepository(
        report_title=req.report_title,
        category=req.category,
        business_description=req.business_description,
        raw_sql=req.raw_sql,
        business_rules_explained=req.business_rules_explained,
        joins_explained=req.joins_explained,
        effective_dating_explained=req.effective_dating_explained,
        tags=req.tags,
        author=current_user.full_name
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    # Refresh RAG vector index
    rag_retriever.reload_sql_repository(db)

    return {"message": "SQL Template successfully published to repository", "id": new_template.id}
