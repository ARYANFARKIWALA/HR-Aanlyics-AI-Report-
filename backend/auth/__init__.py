"""Authentication and authorization package."""
from .dependencies import get_current_user, require_role
from .jwt_handler import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

__all__ = [
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "hash_password",
    "require_role",
    "verify_password"
]
