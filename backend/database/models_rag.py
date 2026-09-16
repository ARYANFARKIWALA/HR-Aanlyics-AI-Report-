"""Module 5: Database Models for RAG Knowledge Base.

Defines tables for:
- rag_documents
- rag_chunks
"""

import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Text, Index, JSON
)
from sqlalchemy.orm import relationship
from .connection import Base


class RAGDocument(Base):
    """Knowledge document holding indexed schema, report, or rule information."""
    __tablename__ = "rag_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(64), unique=True, nullable=False, index=True)  # e.g., DOC-00001

    # Source Type: DATABASE_SCHEMA, TABLE_METADATA, COLUMN_METADATA, SQL_REPORT,
    # SQL_METADATA, BUSINESS_RULE, SECURITY_RULE, EFFECTIVE_DATING_RULE,
    # REPORT_DESCRIPTION, BUSINESS_GLOSSARY
    source_type = Column(String(50), nullable=False, index=True)
    source_id = Column(String(64), nullable=True, index=True)  # e.g., BR-EMP-001, REPORT-101

    title = Column(String(256), nullable=False)
    content = Column(Text, nullable=False)

    database_id = Column(String(64), default="sqlite_hr_default", nullable=False, index=True)
    report_id = Column(Integer, nullable=True, index=True)
    rule_id = Column(Integer, nullable=True, index=True)

    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    chunks = relationship("RAGChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_rag_doc_db_source", "database_id", "source_type", "is_active"),
    )


class RAGChunk(Base):
    """Semantic chunk and vector embedding representation of a knowledge document."""
    __tablename__ = "rag_chunks"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(String(64), unique=True, nullable=False, index=True)  # e.g., CH-00001
    document_id = Column(Integer, ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False, index=True)

    chunk_text = Column(Text, nullable=False)

    # Chunk Type: REPORT_OVERVIEW, TABLE_RELATIONSHIPS, BUSINESS_RULE,
    # EFFECTIVE_DATING, SECURITY_LOGIC, ORIGINAL_SQL, SCHEMA_DEFINITION
    chunk_type = Column(String(50), nullable=False, index=True)

    # Dense vector representation stored as JSON float list
    embedding_json = Column(JSON, nullable=True)

    database_id = Column(String(64), default="sqlite_hr_default", nullable=False, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_id = Column(String(64), nullable=True)
    report_id = Column(Integer, nullable=True)
    rule_id = Column(Integer, nullable=True)

    table_names_json = Column(JSON, nullable=True)  # list of referenced tables
    column_names_json = Column(JSON, nullable=True)  # list of referenced columns

    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    security_level = Column(String(30), default="STANDARD", nullable=False)  # STANDARD, CRITICAL, RESTRICTED

    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    document = relationship("RAGDocument", back_populates="chunks")

    __table_args__ = (
        Index("idx_rag_chunk_db_active", "database_id", "is_active", "chunk_type"),
    )
