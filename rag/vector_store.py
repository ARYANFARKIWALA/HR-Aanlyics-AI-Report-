"""Module 5: Vector Store Layer.

Manages persistence of RAG documents and semantic chunks in the database.
Executes vector similarity search with hard metadata filtering (database_id, is_active, version).
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from backend.database.models_rag import RAGChunk, RAGDocument

from .embedding_service import EmbeddingService

logger = logging.getLogger("rag.vector_store")


class VectorStore:
    """Vector database storage and similarity search engine."""

    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()

    def store_document_and_chunks(
        self,
        doc_data: dict[str, Any],
        chunks: list[Any]
    ) -> RAGDocument:
        """Stores a parent RAG document and its associated semantic chunks."""
        # 1. Check if document already exists
        doc_id = doc_data["document_id"]
        existing_doc = self.db.query(RAGDocument).filter_by(document_id=doc_id).first()

        if existing_doc:
            # Update parent document
            existing_doc.title = doc_data.get("title", existing_doc.title)
            existing_doc.content = doc_data.get("content", existing_doc.content)
            existing_doc.version = doc_data.get("version", existing_doc.version)
            existing_doc.is_active = doc_data.get("is_active", True)
            parent_doc = existing_doc

            # Deactivate or delete old chunks for this document
            self.db.query(RAGChunk).filter_by(document_id=existing_doc.id).delete()
        else:
            parent_doc = RAGDocument(
                document_id=doc_id,
                source_type=doc_data["source_type"],
                source_id=doc_data.get("source_id"),
                title=doc_data["title"],
                content=doc_data.get("content", ""),
                database_id=doc_data.get("database_id", "sqlite_hr_default"),
                report_id=doc_data.get("report_id"),
                rule_id=doc_data.get("rule_id"),
                version=doc_data.get("version", 1),
                is_active=doc_data.get("is_active", True)
            )
            self.db.add(parent_doc)
            self.db.flush()

        # 2. Embed and store chunks
        for c in chunks:
            chunk_text = c.chunk_text if hasattr(c, "chunk_text") else c["chunk_text"]
            embedding = self.embedding_service.generate_embedding(chunk_text)

            db_chunk = RAGChunk(
                chunk_id=c.chunk_id if hasattr(c, "chunk_id") else c["chunk_id"],
                document_id=parent_doc.id,
                chunk_text=chunk_text,
                chunk_type=c.chunk_type if hasattr(c, "chunk_type") else c["chunk_type"],
                embedding_json=embedding,
                database_id=c.database_id if hasattr(c, "database_id") else c["database_id"],
                source_type=c.source_type if hasattr(c, "source_type") else c["source_type"],
                source_id=c.source_id if hasattr(c, "source_id") else c.get("source_id"),
                report_id=c.report_id if hasattr(c, "report_id") else c.get("report_id"),
                rule_id=c.rule_id if hasattr(c, "rule_id") else c.get("rule_id"),
                table_names_json=c.table_names if hasattr(c, "table_names") else c.get("table_names", []),
                column_names_json=c.column_names if hasattr(c, "column_names") else c.get("column_names", []),
                version=c.version if hasattr(c, "version") else c.get("version", 1),
                is_active=c.is_active if hasattr(c, "is_active") else c.get("is_active", True),
                security_level=c.security_level if hasattr(c, "security_level") else c.get("security_level", "STANDARD")
            )
            self.db.add(db_chunk)

        self.db.commit()
        return parent_doc

    def search_similar_chunks(
        self,
        query: str,
        database_id: str,
        top_k: int = 8,
        source_types: list[str] | None = None,
        filter_tables: list[str] | None = None
    ) -> list[tuple[RAGChunk, float]]:
        """Performs vector similarity search filtered strictly by database_id and active status."""
        query_vec = self.embedding_service.generate_embedding(query)

        # Build filter query
        q = self.db.query(RAGChunk).filter(
            RAGChunk.database_id == database_id,
            RAGChunk.is_active == True
        )
        if source_types:
            q = q.filter(RAGChunk.source_type.in_(source_types))

        candidates = q.all()
        scored_chunks: list[tuple[RAGChunk, float]] = []

        for ch in candidates:
            ch_vec = ch.embedding_json
            if ch_vec:
                score = EmbeddingService.cosine_similarity(query_vec, ch_vec)
                scored_chunks.append((ch, score))

        # Sort descending by score
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]

    def deactivate_by_source(self, database_id: str, source_type: str, source_id: str):
        """Deactivates chunks and document when updated or removed."""
        docs = (
            self.db.query(RAGDocument)
            .filter_by(database_id=database_id, source_type=source_type, source_id=source_id)
            .all()
        )
        for d in docs:
            d.is_active = False
            for c in d.chunks:
                c.is_active = False
        self.db.commit()
