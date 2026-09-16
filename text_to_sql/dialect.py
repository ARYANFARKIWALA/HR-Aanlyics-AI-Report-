"""Module 6: Multi-Database Dialect Translation Engine.

Supports:
- PostgreSQL
- MySQL
- SQLite
- SQL Server (T-SQL)
- Oracle

Provides dialect-specific date formatting, temporal arithmetic, limit/top clauses,
string concatenation, and SQLGlot AST transpilation.
"""

import logging
import re

import sqlglot

logger = logging.getLogger("text_to_sql.dialect")

DIALECT_MAPPINGS = {
    "sqlite": "sqlite",
    "postgresql": "postgres",
    "postgres": "postgres",
    "mysql": "mysql",
    "sqlserver": "tsql",
    "mssql": "tsql",
    "oracle": "oracle"
}


class DialectTransformer:
    """Transforms and adapts SQL queries for specific target database engines."""

    @classmethod
    def normalize_dialect_name(cls, dialect: str) -> str:
        """Normalizes dialect string to standard canonical name."""
        d = (dialect or "sqlite").lower().strip()
        return DIALECT_MAPPINGS.get(d, "sqlite")

    @classmethod
    def get_current_date_expression(cls, dialect: str) -> str:
        """Returns the dialect-specific current date expression."""
        norm = cls.normalize_dialect_name(dialect)
        if norm == "postgres":
            return "CURRENT_DATE"
        elif norm == "mysql":
            return "CURDATE()"
        elif norm == "tsql":
            return "CAST(GETDATE() AS DATE)"
        elif norm == "oracle":
            return "TRUNC(SYSDATE)"
        else:
            return "DATE('now')"

    @classmethod
    def get_date_format_expression(cls, column_expr: str, format_type: str, dialect: str) -> str:
        """Returns dialect-specific date formatting (e.g. YYYY-MM)."""
        norm = cls.normalize_dialect_name(dialect)
        if norm == "postgres":
            return f"TO_CHAR({column_expr}, 'YYYY-MM')"
        elif norm == "mysql":
            return f"DATE_FORMAT({column_expr}, '%Y-%m')"
        elif norm == "tsql":
            return f"FORMAT({column_expr}, 'yyyy-MM')"
        elif norm == "oracle":
            return f"TO_CHAR({column_expr}, 'YYYY-MM')"
        else:
            return f"strftime('%Y-%m', {column_expr})"

    @classmethod
    def get_concat_expression(cls, expr_a: str, expr_b: str, dialect: str, separator: str = " ") -> str:
        """Returns dialect-specific string concatenation."""
        norm = cls.normalize_dialect_name(dialect)
        sep_literal = f"'{separator}'"
        if norm == "mysql":
            return f"CONCAT({expr_a}, {sep_literal}, {expr_b})"
        elif norm == "tsql":
            return f"{expr_a} + {sep_literal} + {expr_b}"
        else:
            return f"{expr_a} || {sep_literal} || {expr_b}"

    @classmethod
    def apply_limit(cls, sql: str, limit: int, dialect: str) -> str:
        """Applies dialect-aware pagination or TOP/LIMIT clause."""
        norm = cls.normalize_dialect_name(dialect)
        sql_clean = sql.strip().rstrip(";")

        # Remove existing LIMIT or TOP
        sql_clean = re.sub(r"\s+LIMIT\s+\d+", "", sql_clean, flags=re.IGNORECASE)
        sql_clean = re.sub(r"\s+FETCH\s+FIRST\s+\d+\s+ROWS\s+ONLY", "", sql_clean, flags=re.IGNORECASE)

        if norm == "tsql":
            # SQL Server uses SELECT TOP N
            if re.search(r"^SELECT\s+DISTINCT\s+", sql_clean, re.IGNORECASE):
                return re.sub(r"^SELECT\s+DISTINCT\s+", f"SELECT DISTINCT TOP {limit} ", sql_clean, count=1, flags=re.IGNORECASE)
            else:
                return re.sub(r"^SELECT\s+", f"SELECT TOP {limit} ", sql_clean, count=1, flags=re.IGNORECASE)
        elif norm == "oracle":
            return f"{sql_clean} FETCH FIRST {limit} ROWS ONLY"
        else:
            return f"{sql_clean} LIMIT {limit}"

    @classmethod
    def transpile_sql(cls, sql: str, target_dialect: str, source_dialect: str = "sqlite") -> str:
        """Uses SQLGlot AST transpilation to convert SQL syntax between dialects."""
        src = cls.normalize_dialect_name(source_dialect)
        tgt = cls.normalize_dialect_name(target_dialect)

        if src == tgt:
            return sql.strip().rstrip(";")

        try:
            transpiled = sqlglot.transpile(sql, read=src, write=tgt, pretty=True)
            if transpiled and transpiled[0]:
                return transpiled[0].strip().rstrip(";")
        except Exception as e:
            logger.warning(f"SQLGlot transpilation warning ({src} -> {tgt}): {e}")

        # Fallback if transpiler cannot fully parse custom AST
        return sql.strip().rstrip(";")
