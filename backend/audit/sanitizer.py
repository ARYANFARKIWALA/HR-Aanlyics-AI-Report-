"""Audit Log Data Sanitizer.

Prevents leakage of:
- Passwords & password hashes
- Database connection credentials and connection URLs
- Sensitive personal data (SSN, credit card, bank account)
"""

import re
from typing import Any, Dict, List, Union

REDACTED = "[REDACTED]"

SENSITIVE_KEYS = {
    "password", "hashed_password", "token", "secret", "salt", "access_token",
    "refresh_token", "credentials", "api_key", "ssn", "social_security_number",
    "bank_account", "bank_account_number", "credit_card", "cvv"
}


class AuditDataSanitizer:
    """Sanitizes audit log event payloads before persistence."""

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        if isinstance(data, dict):
            clean_dict = {}
            for k, v in data.items():
                if any(sk in k.lower() for sk in SENSITIVE_KEYS):
                    clean_dict[k] = REDACTED
                else:
                    clean_dict[k] = cls.sanitize(v)
            return clean_dict

        elif isinstance(data, (list, tuple)):
            return [cls.sanitize(item) for item in data]

        elif isinstance(data, str):
            # Scrub database connection strings e.g. postgresql://user:pass@host/db
            scrubbed = re.sub(r"://([^:@\s]+):([^@\s]+)@", "://***:***@", data)
            # Scrub standalone JWT or hash-like long bearer tokens
            scrubbed = re.sub(r"Bearer\s+[A-Za-z0-9\-_\.]+", "Bearer [REDACTED_TOKEN]", scrubbed)
            # Scrub obvious 9-digit SSN
            scrubbed = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "***-**-****", scrubbed)
            return scrubbed

        return data
