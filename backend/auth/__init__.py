"""Authentication and authorization package."""
from .jwt_handler import hash_password, verify_password, create_access_token, decode_access_token
from .dependencies import get_current_user, require_role

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "require_role"
]
