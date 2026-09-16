"""Module 6: AI Text-to-SQL Engine FastAPI Routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from text_to_sql.schemas import TextToSQLRequest, TextToSQLResponse
from text_to_sql.service import TextToSQLService

router = APIRouter(prefix="/api/text-to-sql", tags=["Module 6 - AI Text-to-SQL Engine"])


class ExplainRequest(BaseModel):
    sql: str = Field(..., min_length=5, description="SQL query to explain")
    dialect: str = Field("sqlite", description="Target SQL dialect")


@router.post("/generate", response_model=TextToSQLResponse, summary="Translate natural language to verified SQL")
def generate_sql(req: TextToSQLRequest, db: Session = Depends(get_db)):
    """Translates natural language into dialect-aware, safe SQL with explanation and traceability."""
    svc = TextToSQLService(db)
    try:
        response = svc.generate_sql(req)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan", summary="Generate query plan without SQL generation")
def plan_query(req: TextToSQLRequest, db: Session = Depends(get_db)):
    """Extracts business intent, entities, metrics, dimensions, and join paths."""
    svc = TextToSQLService(db)
    try:
        return svc.plan_only(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain", summary="Explain SQL query in plain English")
def explain_sql(req: ExplainRequest, db: Session = Depends(get_db)):
    """Generates a plain-English, stakeholder-ready explanation of a SQL query."""
    svc = TextToSQLService(db)
    try:
        explanation = svc.explain_only(sql=req.sql, dialect=req.dialect)
        return {"sql": req.sql, "dialect": req.dialect, "explanation": explanation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", summary="Get recent SQL generation history")
def get_generation_history():
    """Returns the list of recently generated queries and their execution plan/audit status."""
    return TextToSQLService.get_history()
