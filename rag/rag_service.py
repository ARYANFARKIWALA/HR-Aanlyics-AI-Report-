"""Module 5: Unified RAG Knowledge Base Service.

Façade coordinating:
- Knowledge Ingestion (Schemas, SQL Reports, Business Rules)
- Hybrid Retrieval (Dense Vector + Keyword + Priority Re-ranking)
- Context Assembly (<ORGANIZATIONAL_KNOWLEDGE> Delimitation & Conflict Detection)
- Knowledge Base Statistics & Maintenance
"""

import logging
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database.connection_manager import connection_manager
from backend.database.models_rag import RAGChunk, RAGDocument

from .context_builder import ContextBuilder
from .ingestion_service import KnowledgeIngestionService
from .retrieval_service import HybridRetrievalService
from .schemas import RAGContextResponse

logger = logging.getLogger("rag.service")


class RAGService:
    """Unified coordinator for the RAG Knowledge Base."""

    def __init__(self, db: Session):
        self.db = db
        self.ingestion_service = KnowledgeIngestionService(db)
        self.retrieval_service = HybridRetrievalService(db)
        self.context_builder = ContextBuilder(db)

    def ingest_database(self, database_id: str = "sqlite_hr_default") -> dict[str, Any]:
        """Ingests all approved rules, verified reports, and schemas for a database."""
        return self.ingestion_service.ingest_all(database_id=database_id)

    def ingest_report(self, report_id: int) -> dict[str, Any]:
        """Ingests a single approved SQL report."""
        return self.ingestion_service.ingest_report(report_id=report_id)

    def ingest_rule(self, rule_id: int) -> dict[str, Any]:
        """Ingests a single approved business rule."""
        return self.ingestion_service.ingest_rule(rule_id=rule_id)

    def ingest_table(self, table_id: int) -> dict[str, Any]:
        """Ingests a single schema table."""
        return self.ingestion_service.ingest_table(table_id=table_id)

    def search(
        self,
        query: str,
        database_id: str = "sqlite_hr_default",
        top_k: int = 8,
        include_schema: bool = True,
        include_rules: bool = True,
        include_reports: bool = True
    ) -> list[dict[str, Any]]:
        """Performs hybrid vector and keyword search with explainability metadata."""
        return self.retrieval_service.retrieve(
            query=query,
            database_id=database_id,
            top_k=top_k,
            include_schema=include_schema,
            include_rules=include_rules,
            include_reports=include_reports
        )

    def get_context_for_query(
        self,
        query: str,
        database_id: str = "sqlite_hr_default",
        top_k: int = 8
    ) -> RAGContextResponse:
        """Retrieves and packages structured organizational knowledge for Text-to-SQL."""
        # Find DB dialect
        try:
            db_type = connection_manager.get_dialect_rules(database_id).dialect
        except Exception:
            db_type = "sqlite"

        chunks = self.search(
            query=query,
            database_id=database_id,
            top_k=top_k
        )
        return self.context_builder.build_context(
            query=query,
            retrieved_chunks=chunks,
            database_id=database_id,
            database_type=db_type
        )


    def retrieve_knowledge(
        self,
        query: str,
        database_id: str = "sqlite_hr_default",
        top_k: int = 10
    ) -> dict[str, Any]:
        """Module 5 Primary Knowledge Retrieval Pipeline.
        
        Executes:
        User Question -> Query Understanding -> Knowledge Retrieval -> Structured Knowledge (SQL+Schema+Rules) -> Context Package
        """
        from .query_analyzer import QueryAnalyzer

        # 1. Query Understanding
        understanding = QueryAnalyzer.analyze(query)

        # 2. Knowledge Retrieval (Hybrid vector + keyword)
        chunks = self.search(
            query=query,
            database_id=database_id,
            top_k=top_k,
            include_schema=True,
            include_rules=True,
            include_reports=True
        )

        # 3. Categorize by knowledge source
        relevant_sql = []
        schema_tables = []
        business_rules = []
        effective_dating_rules = []
        glossary_defs = []

        for c in chunks:
            stype = c.get("source_type", "")
            ctype = c.get("chunk_type", "")

            if stype == "SQL_REPORT":
                relevant_sql.append(c)
            elif stype in ["TABLE_METADATA", "DATABASE_SCHEMA", "COLUMN_METADATA"]:
                schema_tables.append(c)
            elif stype == "BUSINESS_RULE":
                business_rules.append(c)
            elif stype in ["HR_GLOSSARY", "REPORT_DEFINITION"]:
                glossary_defs.append(c)

            if ctype == "EFFECTIVE_DATING" or "effective" in c.get("text", "").lower():
                effective_dating_rules.append(c)

        # 4. Context Package Assembly (injection-safe)
        try:
            db_type = connection_manager.get_dialect_rules(database_id).dialect
        except Exception:
            db_type = "sqlite"

        ctx_res = self.context_builder.build_context(
            query=query,
            retrieved_chunks=chunks,
            database_id=database_id,
            database_type=db_type
        )

        return {
            "query": query,
            "database_id": database_id,
            "query_understanding": understanding,
            "retrieved_knowledge": chunks,
            "relevant_sql": relevant_sql,
            "schema_tables": schema_tables,
            "business_rules": business_rules,
            "effective_dating_rules": effective_dating_rules,
            "glossary_definitions": glossary_defs,
            "context_package": ctx_res.context,
            "total_items_retrieved": len(chunks)
        }


    def get_stats(self, database_id: str | None = None) -> dict[str, Any]:
        """Returns knowledge base statistics, counts, and breakdown."""
        doc_q = self.db.query(RAGDocument).filter_by(is_active=True)
        chunk_q = self.db.query(RAGChunk).filter_by(is_active=True)

        if database_id:
            doc_q = doc_q.filter_by(database_id=database_id)
            chunk_q = chunk_q.filter_by(database_id=database_id)

        total_docs = doc_q.count()
        total_chunks = chunk_q.count()

        # Breakdown by source_type
        source_counts = dict(
            self.db.query(RAGDocument.source_type, func.count(RAGDocument.id))
            .filter(RAGDocument.is_active.is_(True))
            .group_by(RAGDocument.source_type)
            .all()
        )

        # Breakdown by database
        db_counts = dict(
            self.db.query(RAGDocument.database_id, func.count(RAGDocument.id))
            .filter(RAGDocument.is_active.is_(True))
            .group_by(RAGDocument.database_id)
            .all()
        )

        # Breakdown by chunk_type
        chunk_type_counts = dict(
            self.db.query(RAGChunk.chunk_type, func.count(RAGChunk.id))
            .filter(RAGChunk.is_active.is_(True))
            .group_by(RAGChunk.chunk_type)
            .all()
        )

        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "total_embeddings": total_chunks,
            "by_source_type": source_counts,
            "by_database_id": db_counts,
            "by_chunk_type": chunk_type_counts
        }

    def rebuild(self, database_id: str = "sqlite_hr_default") -> dict[str, Any]:
        """Clears and re-ingests knowledge base for a database."""
        # Deactivate or remove existing
        docs = self.db.query(RAGDocument).filter_by(database_id=database_id).all()
        for doc in docs:
            self.db.query(RAGChunk).filter_by(document_id=doc.document_id).delete()
            self.db.delete(doc)
        self.db.commit()

        # Re-ingest
        return self.ingest_database(database_id=database_id)
