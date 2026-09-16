"""Module 5: Prioritized Context Builder.

Structures retrieved knowledge into an injection-safe, prioritized context for Module 6:
- Prioritizes: CRITICAL Security > Mandatory Rules > Effective Dating > SQL Reports > Schemas
- Delimits within <ORGANIZATIONAL_KNOWLEDGE> tags (Prompt Injection Defense)
- Flags rule conflicts
- Identifies INSUFFICIENT_CONTEXT when no approved knowledge sufficiently matches
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.database.models_rules import BusinessRule
from business_rules.conflict_detector import RuleConflictDetector
from .schemas import RAGContextResponse

logger = logging.getLogger("rag.context_builder")


class ContextBuilder:
    """Combines retrieved chunks into structured context for AI Text-to-SQL generation."""

    def __init__(self, db: Session):
        self.db = db

    def build_context(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        database_id: str = "sqlite_hr_default",
        database_type: str = "sqlite"
    ) -> RAGContextResponse:
        """Constructs prioritized context object with prompt injection boundaries."""
        if not retrieved_chunks:
            return RAGContextResponse(
                status="INSUFFICIENT_CONTEXT",
                message="No approved business rule or existing report sufficiently matches this request.",
                query=query,
                database_id=database_id,
                database_type=database_type
            )

        # 1. Bucket chunks by priority category
        security_chunks = []
        mandatory_rule_chunks = []
        effective_dating_chunks = []
        report_chunks = []
        schema_chunks = []
        other_chunks = []

        tables_set = set()
        cols_set = set()
        retrieved_rule_ids = set()

        for c in retrieved_chunks:
            ctype = c.get("chunk_type", "")
            sec = c.get("security_level", "")
            for t in c.get("table_names", []):
                tables_set.add(t)
            for col in c.get("column_names", []):
                cols_set.add(col)
            if c.get("rule_id"):
                retrieved_rule_ids.add(c["rule_id"])

            if sec == "CRITICAL" or ctype == "SECURITY_LOGIC":
                security_chunks.append(c)
            elif ctype == "EFFECTIVE_DATING":
                effective_dating_chunks.append(c)
            elif ctype == "BUSINESS_RULE":
                mandatory_rule_chunks.append(c)
            elif ctype in ["REPORT_OVERVIEW", "ORIGINAL_SQL"]:
                report_chunks.append(c)
            elif ctype in ["SCHEMA_DEFINITION", "TABLE_RELATIONSHIPS"]:
                schema_chunks.append(c)
            else:
                other_chunks.append(c)

        # 2. Check for conflicts among retrieved rules
        conflicts_detected = []
        if len(retrieved_rule_ids) > 1:
            rules = self.db.query(BusinessRule).filter(BusinessRule.id.in_(list(retrieved_rule_ids))).all()
            for i in range(len(rules)):
                for j in range(i + 1, len(rules)):
                    cand_conflicts = RuleConflictDetector.detect_conflicts(
                        candidate_rule={
                            "rule_expression": rules[i].rule_expression,
                            "table_name": rules[i].table_name,
                            "column_name": rules[i].column_name,
                            "database_id": database_id
                        },
                        db=self.db,
                        database_id=database_id,
                        exclude_rule_id=rules[i].id
                    )
                    for cf in cand_conflicts:
                        if cf.get("conflicting_rule_id") == rules[j].id:
                            conflicts_detected.append(cf)

        status_code = "RULE_CONFLICT" if conflicts_detected else "SUCCESS"
        status_msg = "Conflicting business rules detected among retrieved knowledge." if conflicts_detected else None

        # 3. Assemble Prioritized Text
        lines = []
        lines.append("<ORGANIZATIONAL_KNOWLEDGE>")
        lines.append(f"TARGET DATABASE: {database_id} (Dialect: {database_type.upper()})\n")

        # Priority 1: Security Rules
        if security_chunks:
            lines.append("## 1. CRITICAL SECURITY ACCESS POLICIES (MANDATORY ENFORCEMENT):")
            for sc in security_chunks:
                lines.append(f"- {sc['text'].strip()}")
            lines.append("")

        # Priority 2: Mandatory Business Rules
        if mandatory_rule_chunks:
            lines.append("## 2. APPROVED BUSINESS RULES (MANDATORY FILTERS & CONDITIONS):")
            for rc in mandatory_rule_chunks:
                lines.append(f"- {rc['text'].strip()}")
            lines.append("")

        # Priority 3: Effective Dating Rules
        if effective_dating_chunks:
            lines.append("## 3. EFFECTIVE DATING & TEMPORAL POLICIES:")
            for ec in effective_dating_chunks:
                lines.append(f"- {ec['text'].strip()}")
            lines.append("")

        # Priority 4: Existing Verified Reports
        if report_chunks:
            lines.append("## 4. RELEVANT EXISTING SQL REPORTS (PREFER REUSING THESE PATTERNS):")
            for rpc in report_chunks:
                lines.append(f"{rpc['text'].strip()}\n")

        # Priority 5: Schema Definitions & Join Paths
        if schema_chunks:
            lines.append("## 5. DATABASE SCHEMA DEFINITIONS & CANONICAL JOIN PATHS:")
            for sch in schema_chunks:
                lines.append(f"{sch['text'].strip()}\n")

        lines.append("</ORGANIZATIONAL_KNOWLEDGE>")
        context_str = "\n".join(lines)

        return RAGContextResponse(
            status=status_code,
            message=status_msg,
            query=query,
            database_id=database_id,
            database_type=database_type,
            retrieved_documents=retrieved_chunks,
            relevant_tables=sorted(list(tables_set)),
            relevant_columns=sorted(list(cols_set)),
            business_rules=[c for c in mandatory_rule_chunks],
            security_rules=[c for c in security_chunks],
            effective_dating_rules=[c for c in effective_dating_chunks],
            existing_reports=[c for c in report_chunks],
            context=context_str,
            retrieval_scores=[{"chunk_id": c["chunk_id"], "score": c["score"]} for c in retrieved_chunks],
            conflicts_detected=conflicts_detected
        )
