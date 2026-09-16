"""Security, injection defense, and function allowlist validator."""

from typing import Tuple, List, Set
import re
import sqlglot
from sqlglot import exp
from .policy_engine import SAFE_FUNCTIONS, FORBIDDEN_FUNCTIONS
from .schemas import ChecklistItem


class SecurityValidator:
    """Detects SQL injection patterns, dangerous functions, comments, and deep nesting."""

    @staticmethod
    def validate(
        raw_sql: str,
        expression: exp.Expression,
        disallow_comments: bool = True,
        max_subquery_depth: int = 3
    ) -> Tuple[bool, str, List[ChecklistItem], List[str], List[str]]:
        checklist = []
        violations = []
        warnings = []
        sanitized_sql = raw_sql

        # 1. Comments check & sanitation
        has_comments = bool(re.search(r"(--[^\r\n]*)|(/\*[\s\S]*?\*/)", raw_sql))
        if has_comments:
            if disallow_comments:
                checklist.append(ChecklistItem(
                    check_name="sql_comments_check",
                    passed=False,
                    severity="WARNING",
                    details="SQL comments detected. Obfuscation comments are stripped during sanitization."
                ))
                warnings.append("SQL comments detected and sanitized.")
                # Strip comments for sanitized version
                sanitized_sql = re.sub(r"--[^\r\n]*", "", raw_sql)
                sanitized_sql = re.sub(r"/\*[\s\S]*?\*/", "", sanitized_sql).strip()
            else:
                checklist.append(ChecklistItem(
                    check_name="sql_comments_check",
                    passed=True,
                    severity="INFO",
                    details="Comments permitted by policy."
                ))
        else:
            checklist.append(ChecklistItem(
                check_name="sql_comments_check",
                passed=True,
                severity="INFO",
                details="No obfuscation comments found."
            ))

        # 2. Dangerous functions check
        forbidden_used = set()
        for func in expression.find_all(exp.Anonymous, exp.Func):
            func_name = func.name.lower() if hasattr(func, "name") and func.name else ""
            if not func_name and hasattr(func, "key"):
                func_name = str(func.key).lower()

            if func_name in FORBIDDEN_FUNCTIONS:
                forbidden_used.add(func_name)

        if forbidden_used:
            checklist.append(ChecklistItem(
                check_name="safe_function_allowlist",
                passed=False,
                severity="BLOCKER",
                details=f"Forbidden/dangerous SQL functions: {sorted(list(forbidden_used))}"
            ))
            violations.append(f"Security Violation: Forbidden function(s) {sorted(list(forbidden_used))} are blocked.")
            return False, sanitized_sql, checklist, violations, warnings

        checklist.append(ChecklistItem(
            check_name="safe_function_allowlist",
            passed=True,
            severity="INFO",
            details="All SQL functions comply with safe execution whitelist."
        ))

        # 2.5 Credential exfiltration & sensitive field guard
        RESTRICTED_CREDENTIAL_COLS = {
            "password", "hashed_password", "password_hash", "token", "secret", "salt", "pass_hash",
            "ssn", "social_security_number", "bank_account", "bank_account_number", "routing_number",
            "credit_card", "card_number", "cvv", "medical_history", "diagnosis", "health_condition"
        }
        for col in expression.find_all(exp.Column):
            if col.name.lower() in RESTRICTED_CREDENTIAL_COLS:
                checklist.append(ChecklistItem(
                    check_name="sensitive_field_guard",
                    passed=False,
                    severity="BLOCKER",
                    details=f"Query attempts to access restricted sensitive/credential column: '{col.name}'"
                ))
                violations.append(f"Security Violation: Access to sensitive field '{col.name}' is strictly blocked.")
                return False, sanitized_sql, checklist, violations, warnings

        # 3. Subquery depth check
        def get_subquery_depth(node, current_depth=0):
            max_d = current_depth
            for child in node.args.values():
                if isinstance(child, list):
                    for item in child:
                        if isinstance(item, (exp.Select, exp.Subquery)):
                            max_d = max(max_d, get_subquery_depth(item, current_depth + 1))
                elif isinstance(child, (exp.Select, exp.Subquery)):
                    max_d = max(max_d, get_subquery_depth(child, current_depth + 1))
            return max_d

        nesting_depth = get_subquery_depth(expression)
        if nesting_depth > max_subquery_depth:
            checklist.append(ChecklistItem(
                check_name="subquery_depth_limit",
                passed=False,
                severity="WARNING",
                details=f"Subquery nesting depth ({nesting_depth}) exceeds recommended maximum ({max_subquery_depth})."
            ))
            warnings.append(f"Deep subquery nesting ({nesting_depth} levels) may degrade performance.")
        else:
            checklist.append(ChecklistItem(
                check_name="subquery_depth_limit",
                passed=True,
                severity="INFO",
                details=f"Subquery depth ({nesting_depth}) within acceptable limits ({max_subquery_depth})."
            ))

        # 4. Tautology injection scan (e.g. 1=1 or 'a'='a' used as injection)
        for eq in expression.find_all(exp.EQ):
            left_sql = eq.left.sql().strip()
            right_sql = eq.right.sql().strip()
            if left_sql == right_sql and left_sql.replace("'", "").isalnum():
                warnings.append(f"Tautology pattern detected: '{left_sql} = {right_sql}'.")

        return True, sanitized_sql, checklist, violations, warnings
