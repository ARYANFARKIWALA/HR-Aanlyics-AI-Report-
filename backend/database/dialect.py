"""Module 1: Dialect-Awareness Mapping.

Defines first-class mapping:
Database Type -> SQL Dialect -> Generation & Formatting Rules

Establishes:
- Per-dialect date functions (JULIANDAY, AGE, DATEDIFF, CURRENT_DATE, SYSDATE, etc.)
- Per-dialect pagination (LIMIT/OFFSET, TOP, FETCH FIRST n ROWS ONLY)
- Per-dialect string concatenation (||, CONCAT, +)
- Per-dialect casting rules and null handling (COALESCE, IFNULL, ISNULL, NVL)
"""

from enum import Enum
from typing import Any


class DatabaseType(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"


class SQLDialectRules:
    """Generation and validation rules specific to a SQL dialect."""

    def __init__(
        self,
        dialect_name: str,
        limit_syntax: str,  # "LIMIT", "TOP", "FETCH_FIRST"
        current_date_expr: str,
        date_diff_days_expr: str,  # Template: "{end} and {start}"
        string_concat_op: str,
        null_coalesce_func: str,
        supports_ctes: bool = True,
        quote_char: str = '"'
    ):
        self.dialect_name = dialect_name
        self.limit_syntax = limit_syntax
        self.current_date_expr = current_date_expr
        self.date_diff_days_expr = date_diff_days_expr
        self.string_concat_op = string_concat_op
        self.null_coalesce_func = null_coalesce_func
        self.supports_ctes = supports_ctes
        self.quote_char = quote_char

    def format_limit(self, query: str, limit: int) -> str:
        """Applies dialect-specific limit clause."""
        cleaned = query.strip().rstrip(";")
        if self.limit_syntax == "TOP":
            # In SQL Server, TOP goes after SELECT
            import re
            return re.sub(r"^\s*SELECT\b", f"SELECT TOP {limit}", cleaned, count=1, flags=re.IGNORECASE)
        elif self.limit_syntax == "FETCH_FIRST":
            # Oracle 12c+
            return f"{cleaned} OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
        else:
            # Default SQLite, PostgreSQL, MySQL
            return f"{cleaned} LIMIT {limit}"

    def format_tenure_calc(self, start_date_col: str, end_date_col: str) -> str:
        """Generates dialect-correct tenure calculation in years."""
        if self.dialect_name == "sqlite":
            return f"ROUND(CAST((JULIANDAY(COALESCE({end_date_col}, {self.current_date_expr})) - JULIANDAY({start_date_col})) / 365.25 AS FLOAT), 1)"
        elif self.dialect_name == "postgresql":
            return f"ROUND(CAST(EXTRACT(epoch FROM (COALESCE({end_date_col}, {self.current_date_expr}) - {start_date_col})) / 31557600.0 AS NUMERIC), 1)"
        elif self.dialect_name == "mysql":
            return f"ROUND(DATEDIFF(COALESCE({end_date_col}, {self.current_date_expr}), {start_date_col}) / 365.25, 1)"
        elif self.dialect_name == "sqlserver":
            return f"ROUND(CAST(DATEDIFF(day, {start_date_col}, COALESCE({end_date_col}, {self.current_date_expr})) AS FLOAT) / 365.25, 1)"
        elif self.dialect_name == "oracle":
            return f"ROUND(MONTHS_BETWEEN(COALESCE({end_date_col}, {self.current_date_expr}), {start_date_col}) / 12, 1)"
        return f"(COALESCE({end_date_col}, {self.current_date_expr}) - {start_date_col})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "dialect_name": self.dialect_name,
            "limit_syntax": self.limit_syntax,
            "current_date_expr": self.current_date_expr,
            "string_concat_op": self.string_concat_op,
            "null_coalesce_func": self.null_coalesce_func,
            "supports_ctes": self.supports_ctes,
        }


DIALECT_REGISTRY: dict[DatabaseType, SQLDialectRules] = {
    DatabaseType.SQLITE: SQLDialectRules(
        dialect_name="sqlite",
        limit_syntax="LIMIT",
        current_date_expr="CURRENT_DATE",
        date_diff_days_expr="JULIANDAY({end}) - JULIANDAY({start})",
        string_concat_op="||",
        null_coalesce_func="COALESCE",
        supports_ctes=True,
        quote_char='"'
    ),
    DatabaseType.POSTGRESQL: SQLDialectRules(
        dialect_name="postgresql",
        limit_syntax="LIMIT",
        current_date_expr="CURRENT_DATE",
        date_diff_days_expr="DATE_PART('day', {end} - {start})",
        string_concat_op="||",
        null_coalesce_func="COALESCE",
        supports_ctes=True,
        quote_char='"'
    ),
    DatabaseType.MYSQL: SQLDialectRules(
        dialect_name="mysql",
        limit_syntax="LIMIT",
        current_date_expr="CURDATE()",
        date_diff_days_expr="DATEDIFF({end}, {start})",
        string_concat_op="CONCAT",
        null_coalesce_func="IFNULL",
        supports_ctes=True,
        quote_char='`'
    ),
    DatabaseType.SQLSERVER: SQLDialectRules(
        dialect_name="sqlserver",
        limit_syntax="TOP",
        current_date_expr="CAST(GETDATE() AS DATE)",
        date_diff_days_expr="DATEDIFF(day, {start}, {end})",
        string_concat_op="+",
        null_coalesce_func="ISNULL",
        supports_ctes=True,
        quote_char='"'
    ),
    DatabaseType.ORACLE: SQLDialectRules(
        dialect_name="oracle",
        limit_syntax="FETCH_FIRST",
        current_date_expr="TRUNC(SYSDATE)",
        date_diff_days_expr="({end} - {start})",
        string_concat_op="||",
        null_coalesce_func="NVL",
        supports_ctes=True,
        quote_char='"'
    ),
}


def get_dialect_rules(db_type: DatabaseType | str) -> SQLDialectRules:
    """Resolves dialect rules from database type string or enum."""
    if isinstance(db_type, str):
        try:
            db_type = DatabaseType(db_type.lower())
        except ValueError:
            db_type = DatabaseType.SQLITE
    return DIALECT_REGISTRY.get(db_type, DIALECT_REGISTRY[DatabaseType.SQLITE])
