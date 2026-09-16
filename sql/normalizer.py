"""SQL Normalizer & Hasher.

Normalizes SQL queries into a canonical representation for comparison and duplicate detection.
Preserves the original SQL while generating a deterministic SHA-256 hash.
"""

import hashlib
import re

from sqlglot import parse_one


class SQLNormalizer:
    """Normalizes SQL syntax and produces deterministic hashes for duplicate detection."""

    @classmethod
    def normalize(cls, sql_text: str, dialect: str = "sqlite") -> tuple[str, str]:
        """Normalizes an SQL query and returns (normalized_sql, sql_hash).
        
        Preserves semantics while stripping stylistic differences (whitespace, comments, casing).
        """
        if not sql_text or not sql_text.strip():
            return "", hashlib.sha256(b"").hexdigest()

        cleaned = sql_text.strip().rstrip(";")

        # Try SQLGlot canonical normalization
        try:
            parsed = parse_one(cleaned, read=dialect)
            if parsed is not None:
                # Canonical format: uppercase keywords, standard spacing, no comments
                normalized = parsed.sql(pretty=False, comments=False)
                # Lowercase identifiers and canonical spacing for duplicate hashing
                hash_basis = re.sub(r"\s+", " ", normalized.lower()).strip()
                sql_hash = hashlib.sha256(hash_basis.encode("utf-8")).hexdigest()
                return normalized, sql_hash
        except Exception:
            pass

        # Robust regex-based fallback normalization if dialect-specific syntax fails parsing
        fallback = cls._regex_normalize(cleaned)
        hash_basis = re.sub(r"\s+", " ", fallback.lower()).strip()
        sql_hash = hashlib.sha256(hash_basis.encode("utf-8")).hexdigest()
        return fallback, sql_hash

    @classmethod
    def are_structurally_equivalent(cls, sql1: str, sql2: str, dialect: str = "sqlite") -> bool:
        """Determines if two SQL queries are structurally equivalent."""
        _, hash1 = cls.normalize(sql1, dialect=dialect)
        _, hash2 = cls.normalize(sql2, dialect=dialect)
        return bool(hash1 and hash1 == hash2)

    @staticmethod
    def _regex_normalize(sql: str) -> str:
        """Strips SQL comments and standardizes whitespace."""
        # Remove multi-line comments /* ... */
        sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
        # Remove single-line comments -- ...
        sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
        # Collapse whitespace
        sql = re.sub(r"\s+", " ", sql).strip()
        return sql
