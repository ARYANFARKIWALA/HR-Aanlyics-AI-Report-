"""SQL File Parser.

Reads .sql and .txt files, detects and separates multiple queries,
extracts embedded header metadata (Name, Description, Category, Tags),
and preserves the original SQL text intact.
"""

import re
from typing import List, Dict, Any, Optional
import sqlparse


class ParsedSQLFileEntry:
    """Represents a single query extracted from a SQL file."""

    def __init__(
        self,
        query_index: int,
        raw_sql: str,
        extracted_name: Optional[str] = None,
        extracted_description: Optional[str] = None,
        extracted_category: Optional[str] = None,
        extracted_tags: Optional[List[str]] = None,
        filename: Optional[str] = None
    ):
        self.query_index = query_index
        self.raw_sql = raw_sql.strip()
        self.extracted_name = extracted_name
        self.extracted_description = extracted_description
        self.extracted_category = extracted_category
        self.extracted_tags = extracted_tags or []
        self.filename = filename

    @property
    def is_empty(self) -> bool:
        return not bool(self.raw_sql)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_index": self.query_index,
            "raw_sql": self.raw_sql,
            "extracted_name": self.extracted_name,
            "extracted_description": self.extracted_description,
            "extracted_category": self.extracted_category,
            "extracted_tags": self.extracted_tags,
            "filename": self.filename,
        }


class SQLFileParser:
    """Extracts queries and metadata from .sql and .txt file contents."""

    HEADER_NAME_PATTERNS = [
        re.compile(r"--\s*(?:report\s*name|title|name)\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
        re.compile(r"/\*\s*(?:report\s*name|title|name)\s*:\s*(.+?)\*/", re.IGNORECASE | re.DOTALL),
    ]

    HEADER_DESC_PATTERNS = [
        re.compile(r"--\s*(?:description|desc|purpose)\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
        re.compile(r"/\*\s*(?:description|desc|purpose)\s*:\s*(.+?)\*/", re.IGNORECASE | re.DOTALL),
    ]

    HEADER_CAT_PATTERNS = [
        re.compile(r"--\s*(?:category|module|type)\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    ]

    HEADER_TAGS_PATTERNS = [
        re.compile(r"--\s*(?:tags|keywords)\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    ]

    @classmethod
    def parse_content(cls, content: str, filename: Optional[str] = None) -> List[ParsedSQLFileEntry]:
        """Parses file content, separating multiple queries and preserving original SQL."""
        if not content or not content.strip():
            return []

        # Extract file-level metadata headers
        default_name = None
        for pat in cls.HEADER_NAME_PATTERNS:
            m = pat.search(content)
            if m:
                default_name = m.group(1).strip()
                break

        if not default_name and filename:
            # Derive name from filename
            clean_fn = re.sub(r"\.(sql|txt)$", "", filename, flags=re.IGNORECASE)
            default_name = clean_fn.replace("_", " ").replace("-", " ").title()

        default_desc = None
        for pat in cls.HEADER_DESC_PATTERNS:
            m = pat.search(content)
            if m:
                default_desc = m.group(1).strip()
                break

        default_cat = None
        for pat in cls.HEADER_CAT_PATTERNS:
            m = pat.search(content)
            if m:
                default_cat = m.group(1).strip()
                break

        default_tags = []
        for pat in cls.HEADER_TAGS_PATTERNS:
            m = pat.search(content)
            if m:
                tags_raw = m.group(1).strip()
                default_tags = [t.strip() for t in re.split(r"[,;]", tags_raw) if t.strip()]
                break

        # Split into individual statements using sqlparse
        statements = sqlparse.split(content)
        parsed_entries = []

        for idx, stmt in enumerate(statements, 1):
            stmt_clean = stmt.strip()
            # Skip empty or comment-only statements
            stripped_code = re.sub(r"--.*$", "", stmt_clean, flags=re.MULTILINE)
            stripped_code = re.sub(r"/\*.*?\*/", "", stripped_code, flags=re.DOTALL).strip()
            if not stripped_code:
                continue

            # Query-specific title if multiple queries
            q_name = default_name
            if len(statements) > 1 and default_name:
                q_name = f"{default_name} (Part {idx})"

            entry = ParsedSQLFileEntry(
                query_index=idx,
                raw_sql=stmt_clean,
                extracted_name=q_name or (f"Report Query {idx}" if not filename else filename),
                extracted_description=default_desc or "Existing organization SQL report.",
                extracted_category=default_cat or "Other",
                extracted_tags=default_tags,
                filename=filename
            )
            parsed_entries.append(entry)

        return parsed_entries

    @classmethod
    def parse_file(cls, filepath: str) -> List[ParsedSQLFileEntry]:
        """Reads a file from disk and parses its queries."""
        import os
        filename = os.path.basename(filepath)
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return cls.parse_content(content, filename=filename)
