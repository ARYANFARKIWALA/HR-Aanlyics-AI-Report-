"""Statement structure and read-only type validator."""

from typing import Tuple, List, Optional
import re
from sqlglot import exp
from .parser import SQLParseResult
from .schemas import ChecklistItem

FORBIDDEN_COMMAND_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
    "REPLACE", "CREATE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
    "ATTACH", "DETACH", "PRAGMA", "VACUUM", "INTO OUTFILE",
    "LOAD_FILE", "XP_CMDSHELL", "SHUTDOWN", "CALL", "MERGE"
]


class StatementValidator:
    """Enforces single-statement and strict read-only execution invariants."""

    @staticmethod
    def validate(parse_result: SQLParseResult) -> Tuple[bool, List[ChecklistItem], List[str]]:
        checklist = []
        violations = []

        if not parse_result.is_valid_syntax:
            checklist.append(ChecklistItem(
                check_name="syntax_validity",
                passed=False,
                severity="BLOCKER",
                details=f"Syntax Error: {parse_result.syntax_error}"
            ))
            violations.append(f"SQL syntax error: {parse_result.syntax_error}")
            return False, checklist, violations

        checklist.append(ChecklistItem(
            check_name="syntax_validity",
            passed=True,
            severity="INFO",
            details="AST successfully parsed."
        ))

        # 1. Single statement check
        if parse_result.statement_count > 1:
            checklist.append(ChecklistItem(
                check_name="single_statement_enforcement",
                passed=False,
                severity="BLOCKER",
                details=f"Multiple SQL statements ({parse_result.statement_count}) detected. Chaining is strictly prohibited."
            ))
            violations.append("Multiple statements detected. Only a single SELECT query is permitted.")
            return False, checklist, violations
        else:
            checklist.append(ChecklistItem(
                check_name="single_statement_enforcement",
                passed=True,
                severity="INFO",
                details="Single statement verified."
            ))

        root_expr = parse_result.expression
        if root_expr is None:
            violations.append("No valid statement expression.")
            return False, checklist, violations

        # 2. Strict read-only statement type
        # In SQLGlot, SELECT queries or CTEs with SELECT are valid
        is_select = isinstance(root_expr, exp.Select)
        # Check if it is a Union of Selects
        if isinstance(root_expr, exp.Union):
            is_select = True

        if not is_select:
            checklist.append(ChecklistItem(
                check_name="read_only_statement_type",
                passed=False,
                severity="BLOCKER",
                details=f"Statement type '{type(root_expr).__name__}' is not a read-only SELECT."
            ))
            violations.append(f"Non-SELECT statement ({type(root_expr).__name__}) rejected. Only read-only queries are allowed.")
            return False, checklist, violations
        else:
            checklist.append(ChecklistItem(
                check_name="read_only_statement_type",
                passed=True,
                severity="INFO",
                details="Query is a verified SELECT statement."
            ))

        # 3. Defense-in-depth: scan for DDL/DML mutation expressions anywhere in the AST tree
        mutations = [
            exp.Insert, exp.Update, exp.Delete, exp.Drop,
            exp.Alter, exp.Create, exp.Command, exp.Pragma
        ]
        for m_type in mutations:
            found = list(root_expr.find_all(m_type))
            if found:
                checklist.append(ChecklistItem(
                    check_name="mutation_absence",
                    passed=False,
                    severity="BLOCKER",
                    details=f"Nested mutation expression '{m_type.__name__}' found."
                ))
                violations.append(f"Prohibited mutation AST node '{m_type.__name__}' detected.")
                return False, checklist, violations

        checklist.append(ChecklistItem(
            check_name="mutation_absence",
            passed=True,
            severity="INFO",
            details="Zero DDL/DML mutation nodes present in AST."
        ))

        # 4. Keyword regex check against raw SQL for obfuscated multi-commands
        for kw in FORBIDDEN_COMMAND_KEYWORDS:
            pattern = rf"\b{kw}\b"
            if re.search(pattern, parse_result.raw_sql, re.IGNORECASE):
                checklist.append(ChecklistItem(
                    check_name="forbidden_keyword_scan",
                    passed=False,
                    severity="BLOCKER",
                    details=f"Prohibited keyword '{kw}' detected in SQL text."
                ))
                violations.append(f"Prohibited keyword '{kw}' detected.")
                return False, checklist, violations

        checklist.append(ChecklistItem(
            check_name="forbidden_keyword_scan",
            passed=True,
            severity="INFO",
            details="No prohibited SQL keywords found."
        ))

        return True, checklist, violations
