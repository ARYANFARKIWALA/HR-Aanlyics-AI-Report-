"""Module 5: Knowledge Ingestion Service.

Orchestrates full and incremental ingestion of:
- Database Schemas (M1 & M3)
- Approved SQL Reports (M2)
- Approved Business Rules (M4)
into the vector store.
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from backend.database.models_repo import SQLReport
from backend.database.models_rules import BusinessRule
from backend.database.models_schema import SchemaTable

from .document_builder import DocumentBuilder
from .vector_store import VectorStore

logger = logging.getLogger("rag.ingestion_service")


class KnowledgeIngestionService:
    """Orchestrates indexing of knowledge sources into vector chunks."""

    def __init__(self, db: Session):
        self.db = db
        self.builder = DocumentBuilder(db)
        self.vector_store = VectorStore(db)

    def ingest_all(self, database_id: str = "sqlite_hr_default") -> dict[str, Any]:
        """Runs full ingestion for all eligible knowledge for a database_id."""
        built_items = self.builder.build_all_for_database(database_id)

        docs_count = 0
        chunks_count = 0

        for doc_data, chunks in built_items:
            self.vector_store.store_document_and_chunks(doc_data, chunks)
            docs_count += 1
            chunks_count += len(chunks)

        return {
            "success": True,
            "database_id": database_id,
            "documents_indexed": docs_count,
            "chunks_indexed": chunks_count,
            "embeddings_generated": chunks_count
        }

    def ingest_report(self, report_id: int) -> dict[str, Any]:
        """Incrementally ingests a single approved SQL report."""
        rpt = self.db.query(SQLReport).filter_by(id=report_id).first()
        if not rpt:
            raise ValueError(f"SQL Report ID {report_id} not found.")

        if rpt.status not in ["APPROVED", "VALID"]:
            raise ValueError(f"Report '{rpt.report_code}' has status '{rpt.status}'. Only APPROVED or VALID reports can be indexed.")

        doc_data, chunks = self.builder.build_sql_report_document(rpt)
        doc = self.vector_store.store_document_and_chunks(doc_data, chunks)

        return {
            "success": True,
            "document_id": doc.document_id,
            "chunks_count": len(chunks)
        }

    def ingest_rule(self, rule_id: int) -> dict[str, Any]:
        """Incrementally ingests a single approved business rule."""
        rule = self.db.query(BusinessRule).filter_by(id=rule_id).first()
        if not rule:
            raise ValueError(f"Business Rule ID {rule_id} not found.")

        if rule.status != "ACTIVE" or not rule.is_current:
            raise ValueError(f"Rule '{rule.rule_code}' status is '{rule.status}'. Only ACTIVE and current rules can be indexed.")

        doc_data, chunks = self.builder.build_business_rule_document(rule)
        doc = self.vector_store.store_document_and_chunks(doc_data, chunks)

        return {
            "success": True,
            "document_id": doc.document_id,
            "chunks_count": len(chunks)
        }

    def ingest_table(self, table_id: int) -> dict[str, Any]:
        """Incrementally ingests a single schema table."""
        tbl = self.db.query(SchemaTable).filter_by(id=table_id).first()
        if not tbl:
            raise ValueError(f"Schema Table ID {table_id} not found.")

        doc_data, chunks = self.builder.build_schema_table_document(tbl)
        doc = self.vector_store.store_document_and_chunks(doc_data, chunks)

        return {
            "success": True,
            "document_id": doc.document_id,
            "chunks_count": len(chunks)
        }
