"""Module 5: Hybrid Retrieval Service.

Combines:
- Vector similarity search (dense embeddings)
- Keyword & token matching
- Hard metadata filtering (database_id, is_active, version)
- Candidate re-ranking
Provides explainability breakdown ("Why retrieved?").
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.database.models_rag import RAGChunk, RAGDocument
from .vector_store import VectorStore
from .query_analyzer import QueryAnalyzer

logger = logging.getLogger("rag.retrieval_service")


class HybridRetrievalService:
    """Executes hybrid semantic and keyword retrieval with re-ranking."""

    def __init__(self, db: Session):
        self.db = db
        self.vector_store = VectorStore(db)

    def retrieve(
        self,
        query: str,
        database_id: str = "sqlite_hr_default",
        top_k: int = 8,
        include_schema: bool = True,
        include_rules: bool = True,
        include_reports: bool = True
    ) -> List[Dict[str, Any]]:
        """Executes hybrid retrieval over active knowledge chunks."""
        # 1. Query Analysis
        analysis = QueryAnalyzer.analyze(query)
        cand_tables = [t.lower() for t in analysis.get("candidate_tables", [])]
        q_tokens = set(re.sub(r"[^\w\s]", "", query.lower()).split())

        # Determine source type filter
        source_types = []
        if include_schema:
            source_types.extend(["DATABASE_SCHEMA", "TABLE_METADATA", "COLUMN_METADATA"])
        if include_rules:
            source_types.extend(["BUSINESS_RULE", "SECURITY_RULE", "EFFECTIVE_DATING_RULE", "HR_GLOSSARY"])
        if include_reports:
            source_types.extend(["SQL_REPORT", "SQL_METADATA", "REPORT_DESCRIPTION", "REPORT_DEFINITION"])


        # 2. Vector Search Candidates (Fetch broader candidate pool for re-ranking)
        candidate_k = max(75, top_k * 5)
        vector_candidates = self.vector_store.search_similar_chunks(
            query=query,
            database_id=database_id,
            top_k=candidate_k,
            source_types=source_types
        )

        # 2b. Domain Rule Grounding: Ensure active effective-dating and security rules for candidate tables enter re-ranking
        cand_chunk_ids = {c[0].chunk_id for c in vector_candidates}
        if cand_tables:
            eff_chunks = (
                self.db.query(RAGChunk)
                .filter(
                    RAGChunk.database_id == database_id,
                    RAGChunk.is_active == True,
                    RAGChunk.chunk_type.in_(["EFFECTIVE_DATING", "SECURITY_LOGIC"])
                )
                .all()
            )
            for ech in eff_chunks:
                ech_tables = [t.lower() for t in (ech.table_names_json or [])]
                if any(t in cand_tables for t in ech_tables) and ech.chunk_id not in cand_chunk_ids:
                    vector_candidates.append((ech, 0.40))
                    cand_chunk_ids.add(ech.chunk_id)



        scored_results: List[Dict[str, Any]] = []

        for chunk, v_score in vector_candidates:
            text_clean = chunk.chunk_text.lower()
            chunk_tokens = set(re.sub(r"[^\w\s]", "", text_clean).split())

            # Keyword matching score
            kw_match = len(q_tokens & chunk_tokens) / len(q_tokens) if q_tokens else 0.0

            # Table match bonus
            table_match = False
            chunk_tables = [t.lower() for t in (chunk.table_names_json or [])]
            if any(t in cand_tables for t in chunk_tables):
                table_match = True

            # Priority / Mandatory bonus
            priority_bonus = 0.15 if chunk.security_level == "CRITICAL" else 0.0
            if chunk.chunk_type == "EFFECTIVE_DATING" and table_match:
                priority_bonus += 0.15

            # Composite Re-ranking Score
            composite_score = (0.55 * v_score) + (0.30 * min(1.0, kw_match * 1.5)) + priority_bonus
            if table_match:
                composite_score += 0.10


            final_score = round(min(1.0, composite_score), 3)

            # "Why retrieved?" explanation breakdown
            why_retrieved = {
                "semantic_similarity": round(v_score, 3),
                "keyword_match_ratio": round(kw_match, 2),
                "matched_tables": [t for t in chunk_tables if t in cand_tables],
                "is_critical_security": chunk.security_level == "CRITICAL",
                "database_id": chunk.database_id
            }

            scored_results.append({
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document.document_id if chunk.document else "",
                "title": chunk.document.title if chunk.document else "",
                "source_type": chunk.source_type,
                "source_id": chunk.source_id or "",
                "chunk_type": chunk.chunk_type,

                "text": chunk.chunk_text,
                "score": final_score,
                "relevance_score": final_score,
                "table_names": chunk.table_names_json or [],

                "column_names": chunk.column_names_json or [],
                "rule_id": chunk.rule_id,
                "report_id": chunk.report_id,
                "security_level": chunk.security_level,
                "why_retrieved": why_retrieved
            })

        # Sort descending by composite score
        scored_results.sort(key=lambda x: x["score"], reverse=True)

        # Deduplicate and ensure diverse knowledge source representation (max 2 chunks per doc)
        final_results = []
        doc_counts = {}
        seen_chunks = set()

        for res in scored_results:
            cid = res["chunk_id"]
            did = res["document_id"]
            if cid in seen_chunks:
                continue
            seen_chunks.add(cid)

            if doc_counts.get(did, 0) >= 2:
                continue
            doc_counts[did] = doc_counts.get(did, 0) + 1
            final_results.append(res)
            if len(final_results) >= top_k:
                break

        return final_results

