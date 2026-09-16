"""Module 4: Business Rule Duplicate Detector.

Identifies exact and near-duplicate business rules using:
- Normalized SQL expression equality
- Natural language token overlap / Jaccard similarity
"""

import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from backend.database.models_rules import BusinessRule

logger = logging.getLogger("business_rules.duplicate")


class RuleDuplicateDetector:
    """Detects syntactic and semantic duplicates across business rules."""

    @classmethod
    def detect_duplicates(
        cls,
        candidate_rule: dict[str, Any],
        db: Session,
        database_id: str | None = None,
        threshold: float = 0.80,
        exclude_rule_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Scans database for identical or highly similar business rules."""
        db_id = candidate_rule.get("database_id") or database_id or "sqlite_hr_default"
        cand_expr = cls._normalize_text(candidate_rule.get("rule_expression") or "")
        cand_nl = cls._normalize_text(candidate_rule.get("natural_language_rule") or "")

        query = db.query(BusinessRule).filter(
            BusinessRule.database_id == db_id,
            BusinessRule.is_current == True
        )
        if exclude_rule_id:
            query = query.filter(BusinessRule.id != exclude_rule_id)

        existing = query.all()
        duplicates = []

        cand_tokens = set(cand_nl.split())

        for r in existing:
            r_expr = cls._normalize_text(r.rule_expression)
            r_nl = cls._normalize_text(r.natural_language_rule)

            # 1. Exact or normalized SQL match
            if cand_expr and r_expr and cand_expr == r_expr:
                duplicates.append({
                    "existing_rule_id": r.id,
                    "existing_rule_code": r.rule_code,
                    "existing_rule_name": r.rule_name,
                    "similarity_score": 1.0,
                    "match_type": "EXACT_EXPRESSION",
                    "reason": "Exact matching SQL / logical filter expression."
                })
                continue

            # 2. Semantic text & token similarity
            import difflib
            r_tokens = set(r_nl.split())
            seq_sim = round(difflib.SequenceMatcher(None, cand_nl, r_nl).ratio(), 2)
            jaccard_sim = 0.0
            if cand_tokens and r_tokens:
                intersection = len(cand_tokens & r_tokens)
                union = len(cand_tokens | r_tokens)
                jaccard_sim = round(intersection / union, 2) if union > 0 else 0.0

            similarity = max(seq_sim, jaccard_sim)
            if similarity >= threshold:
                duplicates.append({
                    "existing_rule_id": r.id,
                    "existing_rule_code": r.rule_code,
                    "existing_rule_name": r.rule_name,
                    "similarity_score": similarity,
                    "match_type": "SEMANTIC_SIMILARITY",
                    "reason": f"High textual similarity ({int(similarity * 100)}%) in natural language rule definition."
                })


        return duplicates

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        """Strips whitespace, punctuation, and converts to lowercase for canonical comparison."""
        t = re.sub(r"[^\w\s]", "", text.lower())
        return re.sub(r"\s+", " ", t).strip()
