"""RAG Knowledge Base & Policy Retrieval API routes (Module 5)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from rag.ingestion import DocumentIngester
from rag.rag_service import RAGService
from rag.retrieval import rag_retriever
from rag.schemas import (
    Phase5RetrievalRequest,
    Phase5RetrievalResponse,
    RAGContextResponse,
    RAGSearchRequest,
)

router = APIRouter(prefix="/api/rag", tags=["Module 5 - RAG Knowledge Base"])


class IngestRequest(BaseModel):
    database_id: str = Field("sqlite_hr_default", description="Database to ingest")


class ContextQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language question")
    database_id: str = Field("sqlite_hr_default", description="Target database identifier")
    top_k: int | None = Field(8, ge=1, le=30, description="Max chunks to retrieve")


class PolicyQuestionRequest(BaseModel):
    question: str


# =========================================================================
# Module 5: Enterprise Knowledge Ingestion & Retrieval Endpoints
# =========================================================================

@router.post("/ingest", summary="Run full ingestion for a database")
def ingest_database(req: IngestRequest, db: Session = Depends(get_db)):
    """Indexes all approved business rules, SQL reports, and database schema into RAG."""
    svc = RAGService(db)
    try:
        res = svc.ingest_database(database_id=req.database_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/report/{report_id}", summary="Ingest single approved SQL report")
def ingest_report(report_id: int, db: Session = Depends(get_db)):
    """Incrementally indexes a single approved SQL report into the vector store."""
    svc = RAGService(db)
    try:
        return svc.ingest_report(report_id=report_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/rule/{rule_id}", summary="Ingest single approved business rule")
def ingest_rule(rule_id: int, db: Session = Depends(get_db)):
    """Incrementally indexes a single approved business rule into the vector store."""
    svc = RAGService(db)
    try:
        return svc.ingest_rule(rule_id=rule_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/table/{table_id}", summary="Ingest single schema table")
def ingest_table(table_id: int, db: Session = Depends(get_db)):
    """Incrementally indexes a single schema table definition into the vector store."""
    svc = RAGService(db)
    try:
        return svc.ingest_table(table_id=table_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", summary="Hybrid search over organizational knowledge")
def search_knowledge(req: RAGSearchRequest, db: Session = Depends(get_db)):
    """Executes dense vector similarity + keyword matching with explainable scores."""
    svc = RAGService(db)
    try:
        results = svc.search(
            query=req.query,
            database_id=req.database_id,
            top_k=req.top_k or 8,
            include_schema=req.include_schema if req.include_schema is not None else True,
            include_rules=req.include_rules if req.include_rules is not None else True,
            include_reports=req.include_reports if req.include_reports is not None else True,
        )
        return {
            "query": req.query,
            "database_id": req.database_id,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve", response_model=Phase5RetrievalResponse, summary="Phase 5: Knowledge Retrieval Pipeline")
def retrieve_knowledge(req: Phase5RetrievalRequest, db: Session = Depends(get_db)):
    """Phase 5: Retrieves structured HR knowledge (SQL + Schema + Rules + Glossary) with complete source tracking."""
    svc = RAGService(db)
    try:
        return svc.retrieve_knowledge(
            query=req.query,
            database_id=req.database_id,
            top_k=req.top_k or 10
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context", response_model=RAGContextResponse, summary="Assemble prioritized context for Text-to-SQL")
def get_rag_context(req: ContextQueryRequest, db: Session = Depends(get_db)):

    """Retrieves and structures knowledge delimited by <ORGANIZATIONAL_KNOWLEDGE>."""
    svc = RAGService(db)
    try:
        return svc.get_context_for_query(
            query=req.query,
            database_id=req.database_id,
            top_k=req.top_k or 8
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", summary="Get knowledge base statistics")
def get_rag_stats(database_id: str | None = None, db: Session = Depends(get_db)):
    """Returns total documents, chunks, and source type distributions."""
    svc = RAGService(db)
    return svc.get_stats(database_id=database_id)


@router.post("/rebuild", summary="Rebuild entire knowledge base for a database")
def rebuild_knowledge(req: IngestRequest, db: Session = Depends(get_db)):
    """Clears and re-indexes all approved knowledge for the specified database."""
    svc = RAGService(db)
    try:
        return svc.rebuild(database_id=req.database_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# Legacy Prototype Endpoints (Preserved for compatibility)
# =========================================================================

@router.post("/ask", summary="[Legacy] Ask policy question")
def ask_policy_question(req: PolicyQuestionRequest):
    """Retrieves relevant HR policies and returns an AI answer with citations."""
    if not rag_retriever._initialized:
        rag_retriever.initialize()

    return rag_retriever.answer_policy_question(req.question)


@router.get("/policies", summary="[Legacy] List policies")
def list_policies():
    """Lists standard company HR policies indexed in knowledge base."""
    policies = DocumentIngester.get_all_policies()
    return [p.to_dict() for p in policies]
