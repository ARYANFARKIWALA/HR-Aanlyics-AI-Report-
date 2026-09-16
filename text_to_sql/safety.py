"""Module 6: SQL Safety & Hallucination Defense.

Enforces:
1. Strict Read-Only Invariant: Only SELECT / WITH statements permitted.
2. Injection & Mutation Prevention: Blocks DROP, DELETE, INSERT, UPDATE, ALTER, etc.
3. Multi-statement Execution Rejection (anti-SQL injection).
4. Schema Hallucination Detection: Validates that all tables and columns in the AST
   exist in the target database schema allowlist (excluding CTEs and aliases).
"""

import re
import logging
from typing import Dict, Any, List, Set, Optional, Tuple
import sqlglot
from sqlglot import exp

logger = logging.getLogger("text_to_sql.safety")

BLOCKED_KEYWORDS = {
    "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE",
    "GRANT", "REVOKE", "EXEC", "EXECUTE", "MERGE", "CALL",
    "CREATE", "REPLACE", "UPSERT"
}


DIALECT_PARSE_MAP = {
    "sqlite": "sqlite",
    "postgresql": "postgres",
    "postgres": "postgres",
    "mysql": "mysql",
    "sqlserver": "tsql",
    "tsql": "tsql",
    "mssql": "tsql",
    "oracle": "oracle"
}


class SQLSafetyValidator:
    """Validates SQL safety and verifies AST against database schema allowlists."""

    @classmethod
    def validate_safety(cls, sql: str, dialect: str = "sqlite") -> Dict[str, Any]:
        """Verifies that SQL is strictly read-only and free of destructive statements."""
        if not sql or not sql.strip():
            return {
                "is_safe": False,
                "reason": "SQL expression cannot be empty."
            }

        sql_clean = sql.strip()
        norm_dialect = DIALECT_PARSE_MAP.get(dialect.lower().strip(), "sqlite")

        # 1. Multi-statement check
        statements = [s.strip() for s in sql_clean.split(";") if s.strip()]
        if len(statements) > 1:
            return {
                "is_safe": False,
                "reason": "Multiple SQL statements detected. Only a single SELECT query is permitted."
            }

        target_stmt = statements[0]

        # 2. Block destructive commands via regex / token check
        first_word = target_stmt.split()[0].upper() if target_stmt.split() else ""
        if first_word in BLOCKED_KEYWORDS:
            return {
                "is_safe": False,
                "reason": f"Destructive command '{first_word}' is forbidden. Read-only queries only."
            }

        # Check for mutation keywords in statement
        for kw in BLOCKED_KEYWORDS:
            pattern = rf"\b{kw}\b"
            if re.search(pattern, target_stmt, re.IGNORECASE):
                # Ensure it's not part of an identifier or safe word
                # Check with SQLGlot AST
                try:
                    parsed = sqlglot.parse_one(target_stmt, read=norm_dialect)
                    if not isinstance(parsed, (exp.Select, exp.Union)):
                        return {
                            "is_safe": False,
                            "reason": f"Statement contains forbidden mutation operation '{kw}'."
                        }
                except Exception:
                    return {
                        "is_safe": False,
                        "reason": f"Potentially dangerous keyword '{kw}' detected in query."
                    }

        # 3. AST Check: Must be Select or Union
        try:
            parsed = sqlglot.parse_one(target_stmt, read=norm_dialect)
            if not isinstance(parsed, (exp.Select, exp.Union)):
                return {
                    "is_safe": False,
                    "reason": f"Root SQL expression must be a SELECT or CTE statement, got {type(parsed).__name__}."
                }
        except Exception as pe:
            return {
                "is_safe": False,
                "reason": f"Syntax parsing failed: {pe}"
            }

        return {
            "is_safe": True,
            "reason": "Passed read-only safety validation."
        }

    @classmethod
    def detect_hallucinations(
        cls,
        sql: str,
        allowed_tables: Set[str],
        allowed_columns: Optional[Dict[str, Set[str]]] = None,
        dialect: str = "sqlite"
    ) -> Dict[str, Any]:
        """Detects if generated SQL references non-existent tables or columns."""
        norm_dialect = DIALECT_PARSE_MAP.get(dialect.lower().strip(), "sqlite")
        try:
            parsed = sqlglot.parse_one(sql, read=norm_dialect)
        except Exception as e:
            return {
                "has_hallucinations": True,
                "unknown_tables": [],
                "unknown_columns": [],
                "reason": f"Unable to parse SQL for hallucination check: {e}"
            }

        # Collect CTE aliases and SELECT aliases defined in the query
        cte_aliases = set()
        for cte in parsed.find_all(exp.CTE):
            alias = cte.alias
            if alias:
                cte_aliases.add(alias.lower())

        select_aliases = set()
        for alias_node in parsed.find_all(exp.Alias):
            if alias_node.alias:
                select_aliases.add(alias_node.alias.lower())

        # Check tables
        unknown_tables = set()
        normalized_allowed_tables = {t.lower() for t in allowed_tables}

        table_alias_map = {}
        for tbl in parsed.find_all(exp.Table):
            t_name = tbl.name.lower()
            t_alias = tbl.alias.lower() if tbl.alias else t_name

            if t_name in cte_aliases:
                continue

            table_alias_map[t_alias] = t_name

            if t_name not in normalized_allowed_tables:
                unknown_tables.add(t_name)

        # Check columns if allowed_columns dictionary provided: {table_name: set_of_columns}
        unknown_columns = set()
        if allowed_columns:
            norm_col_map = {t.lower(): {c.lower() for c in cols} for t, cols in allowed_columns.items()}
            all_known_cols = set()
            for cols in norm_col_map.values():
                all_known_cols.update(cols)

            for col in parsed.find_all(exp.Column):
                col_name = col.name.lower()
                tbl_ref = col.table.lower() if col.table else None

                # Skip wildcard, literal numbers, star
                if col_name in ("*", ""):
                    continue

                if tbl_ref:
                    actual_table = table_alias_map.get(tbl_ref, tbl_ref)
                    if actual_table in cte_aliases:
                        continue
                    if actual_table in norm_col_map:
                        if col_name not in norm_col_map[actual_table]:
                            unknown_columns.add(f"{actual_table}.{col_name}")
                else:
                    # Unqualified column: must exist in at least one known table or be an alias
                    if col_name not in all_known_cols and col_name not in select_aliases:
                        unknown_columns.add(col_name)

        has_hallucinations = len(unknown_tables) > 0 or len(unknown_columns) > 0

        return {
            "has_hallucinations": has_hallucinations,
            "unknown_tables": sorted(list(unknown_tables)),
            "unknown_columns": sorted(list(unknown_columns)),
            "reason": f"Unknown schema entities detected: tables={list(unknown_tables)}, columns={list(unknown_columns)}" if has_hallucinations else None
        }
