"""Adversarial Penetration & Prompt Injection Defense Tester for Module 13."""


from sqlalchemy.orm import Session

from sql_validator.schemas import SQLValidationRequest
from sql_validator.service import SQLValidatorService

from .schemas import AdversarialTestResult

ADVERSARIAL_ATTACK_SUITE = [
    {
        "attack_type": "Stacked Mutation Attack",
        "payload": "SELECT id FROM departments; DROP TABLE users;",
        "role": "admin"
    },
    {
        "attack_type": "Unauthorized Data Tampering",
        "payload": "UPDATE compensation_history SET base_salary = 999999 WHERE employee_id = 1;",
        "role": "hr_analyst"
    },
    {
        "attack_type": "Destructive Truncate Attack",
        "payload": "TRUNCATE TABLE employees;",
        "role": "admin"
    },
    {
        "attack_type": "Sensitive Credential Union Injection",
        "payload": "SELECT id, name FROM departments UNION SELECT id, hashed_password FROM users;",
        "role": "hr_analyst"
    },
    {
        "attack_type": "Tautology Comment Evasion",
        "payload": "SELECT * FROM employees WHERE 1=1; -- bypass",
        "role": "hr_analyst"
    },
    {
        "attack_type": "Dangerous Function Invocation",
        "payload": "SELECT load_extension('malicious.dll');",
        "role": "admin"
    },
    {
        "attack_type": "Schema Hallucination Probe",
        "payload": "SELECT credit_card_number, ssn FROM confidential_vault;",
        "role": "hr_analyst"
    }
]


class AdversarialSecurityRunner:
    """Stress tests Module 7 SQL Validator and zero-trust gating under adversarial attacks."""

    @classmethod
    def run_penetration_tests(cls, db: Session) -> list[AdversarialTestResult]:
        """Runs the adversarial test suite and verifies all attacks are blocked."""
        validator = SQLValidatorService(db=db)
        results: list[AdversarialTestResult] = []

        for attack in ADVERSARIAL_ATTACK_SUITE:
            atype = attack["attack_type"]
            payload = attack["payload"]
            role = attack.get("role", "hr_analyst")

            val_res = validator.validate_query(SQLValidationRequest(
                sql=payload,
                database_id="sqlite_hr_default",
                user_role=role
            ))

            blocked = (val_res.status == "REJECTED")
            details = "; ".join(val_res.violations) if val_res.violations else ("Passed unexpectedly" if not blocked else "Blocked")

            results.append(AdversarialTestResult(
                attack_type=atype,
                payload=payload,
                blocked=blocked,
                blocked_by="Module 7 Zero-Trust Validator Gate",
                details=details
            ))

        return results
