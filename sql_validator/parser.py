"""SQLGlot AST parser and syntax analyzer for SQL Validator."""

import sqlglot
from sqlglot import exp


class SQLParseResult:
    def __init__(
        self,
        raw_sql: str,
        is_valid_syntax: bool = True,
        syntax_error: str | None = None,
        statements: list[exp.Expression] | None = None,
        dialect: str = "sqlite"
    ):
        self.raw_sql = raw_sql
        self.is_valid_syntax = is_valid_syntax
        self.syntax_error = syntax_error
        self.statements = statements or []
        self.dialect = dialect

    @property
    def expression(self) -> exp.Expression | None:
        return self.statements[0] if self.statements else None

    @property
    def statement_count(self) -> int:
        return len(self.statements)


class SQLValidatorParser:
    """Parses SQL queries into ASTs with comprehensive syntax verification."""

    @staticmethod
    def parse(sql: str, dialect: str = "sqlite") -> SQLParseResult:
        """Parses raw SQL text into AST statements."""
        if not sql or not sql.strip():
            return SQLParseResult(raw_sql=sql, is_valid_syntax=False, syntax_error="SQL query is empty.")

        clean_sql = sql.strip()
        # Map dialect names to sqlglot dialects
        dialect_map = {
            "postgresql": "postgres",
            "postgres": "postgres",
            "sqlite": "sqlite",
            "mysql": "mysql",
            "mssql": "tsql",
            "oracle": "oracle"
        }
        glot_dialect = dialect_map.get(dialect.lower(), "sqlite")

        try:
            parsed = sqlglot.parse(clean_sql, read=glot_dialect)
            # Filter out empty statements
            parsed = [p for p in parsed if p is not None]
            if not parsed:
                return SQLParseResult(raw_sql=clean_sql, is_valid_syntax=False, syntax_error="No valid SQL statements found.")
            return SQLParseResult(raw_sql=clean_sql, is_valid_syntax=True, statements=parsed, dialect=glot_dialect)
        except Exception as e:
            return SQLParseResult(raw_sql=clean_sql, is_valid_syntax=False, syntax_error=str(e), dialect=glot_dialect)
