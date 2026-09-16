"""Password hashing, verification, and policy enforcement."""

import hashlib
import hmac
import os
import re

SALT = os.getenv("AUTH_STATIC_SALT", "hr_secure_static_salt_2026")
ITERATIONS = int(os.getenv("AUTH_HASH_ITERATIONS", "100000"))


def hash_password(password: str, salt: str = SALT) -> str:
    """Hashes password using PBKDF2 HMAC-SHA256 with 100,000 rounds."""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        ITERATIONS
    )
    return dk.hex()


def verify_password(plain_password: str, hashed_password: str, salt: str = SALT) -> bool:
    """Verifies a plain password against its hash using constant-time comparison."""
    calculated = hash_password(plain_password, salt=salt)
    return hmac.compare_digest(calculated, hashed_password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validates enterprise password policy:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one numeric digit
    - At least one special character (@, $, !, %, *, ?, &, #, ^, etc.)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one numeric digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, "Password meets complexity requirements."


class PasswordManager:
    hash_password = staticmethod(hash_password)
    verify_password = staticmethod(verify_password)
    validate_password_strength = staticmethod(validate_password_strength)
