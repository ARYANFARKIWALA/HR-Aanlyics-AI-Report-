"""FastAPI Application Main Entry Point.

HR Analytics AI Report Builder API.
"""

import os
from contextlib import asynccontextmanager
import json
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

from .database.connection import init_db, SessionLocal
from .database.connection_manager import connection_manager
from .database.seeder import seed_database
from rag.retrieval import rag_retriever
from .api import (
    auth_router,
    query_router,
    sql_repo_router,
    rag_router,
    analytics_router,
    report_router,
    database_router,
    sql_repository_router,
    schema_router,
    business_rule_router,
    text_to_sql_router,
    sql_validator_router,
    query_execution_router,
    report_builder_router,
    report_lifecycle_router,
    evaluation_router
)




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database schema, seed data, and RAG vector indices on startup."""
    print("[Startup] Initializing HR Analytics AI platform...")
    init_db()
    seed_database()

    # Initialize RAG indices
    session = SessionLocal()
    try:
        rag_retriever.initialize(session)
        print("[Startup] RAG Vector indices initialized.")
    finally:
        session.close()

    yield
    print("[Shutdown] Cleaning up resources...")


app = FastAPI(
    title="HR Analytics AI Report Builder API",
    description="Enterprise reporting assistant translating natural language to verified SQL, policy RAG, and automated reports.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for Streamlit and external web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router)
app.include_router(query_router)
app.include_router(sql_repo_router)
app.include_router(rag_router)
app.include_router(analytics_router)
app.include_router(report_router)
app.include_router(database_router)
app.include_router(sql_repository_router)
app.include_router(schema_router)
app.include_router(business_rule_router)
app.include_router(text_to_sql_router)
app.include_router(sql_validator_router)
app.include_router(query_execution_router)
app.include_router(report_builder_router)
app.include_router(report_lifecycle_router)
app.include_router(evaluation_router)




@app.get("/")
def root():
    return {
        "app_name": "HR-Analytics-AI-Report-Builder",
        "status": "online",
        "version": "2.0.0",
        "docs_url": "/docs",
        "modules": {
            "M1_Database_Connection_Schema": "Multi-database support with per-engine connectors, explicit database_id, dialect awareness, schema discovery, and credential encryption",
            "M2_SQL_Repository_Catalog": "Pre-loaded complex HR SQL templates with effective dating & business rules",
            "M3_Text_to_SQL": "Natural language to SQL with semantic repository matching & AST validation",
            "M4_SQL_Explainer": "Plain English translations of complex joins & filters",
            "M5_Policy_RAG": "Vector retrieval over HR handbooks & guidelines",
            "M6_Analytics_Visualizer": "Plotly charts & executive KPI calculators",
            "M7_Automated_Reports": "Boardroom-ready PDF & multi-tab Excel workbooks",
            "M8_Security_Audit": "RBAC role enforcement, PII masking, and audit trails"
        }
    }


@app.get("/health")
@app.get("/api/health")
def health_check():
    """Liveness probe reporting overall application health."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "database": "connected",
        "databases_registered": len(connection_manager.list_databases_safe()),
        "rag_indexed": bool(getattr(rag_retriever, "_initialized", False))
    }


@app.get("/ready")
def readiness_check():
    """Readiness probe verifying database and core dependencies before receiving traffic."""
    db_ok = True
    session = None
    try:
        session = SessionLocal()
        session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    finally:
        if session:
            session.close()

    registered_dbs = connection_manager.list_databases_safe()
    cm_ok = len(registered_dbs) > 0
    rag_ok = bool(getattr(rag_retriever, "_initialized", False))

    is_ready = db_ok and cm_ok
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return Response(
        content=json.dumps({
            "status": "ready" if is_ready else "not_ready",
            "dependencies": {
                "metadata_database": "ok" if db_ok else "unavailable",
                "connection_manager": "ok" if cm_ok else "unavailable",
                "registered_databases": len(registered_dbs),
                "rag_retriever": "ok" if rag_ok else "uninitialized"
            }
        }),
        status_code=status_code,
        media_type="application/json"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
