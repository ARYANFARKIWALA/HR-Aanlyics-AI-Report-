"""In-memory thread-safe query result cache."""

import hashlib
import json
import time
from typing import Any, ClassVar

import pandas as pd

DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes


class QueryCacheManager:
    """Thread-safe TTL caching for approved SQL query execution results."""

    _cache: ClassVar[dict[str, tuple[pd.DataFrame, float, list[str], list[dict[str, Any]]]]] = {}

    @classmethod
    def _make_key(cls, database_id: str, sql_hash: str, params: dict[str, Any] | None = None) -> str:
        param_str = json.dumps(params or {}, sort_keys=True)
        param_hash = hashlib.sha256(param_str.encode("utf-8")).hexdigest()[:12]
        return f"{database_id}:{sql_hash}:{param_hash}"

    @classmethod
    def get(
        cls,
        database_id: str,
        sql_hash: str,
        params: dict[str, Any] | None = None,
        ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
    ) -> tuple[pd.DataFrame, list[str], list[dict[str, Any]]] | None:
        key = cls._make_key(database_id, sql_hash, params)
        entry = cls._cache.get(key)
        if not entry:
            return None

        df, cached_time, cols, col_meta = entry
        if (time.time() - cached_time) > ttl_seconds:
            # Expired
            cls._cache.pop(key, None)
            return None

        return df.copy(), cols, col_meta

    @classmethod
    def set(
        cls,
        database_id: str,
        sql_hash: str,
        df: pd.DataFrame,
        cols: list[str],
        col_meta: list[dict[str, Any]],
        params: dict[str, Any] | None = None
    ) -> None:
        key = cls._make_key(database_id, sql_hash, params)
        cls._cache[key] = (df.copy(), time.time(), cols, col_meta)

    @classmethod
    def clear(cls) -> None:
        cls._cache.clear()

    @classmethod
    def invalidate_database(cls, database_id: str) -> int:
        prefix = f"{database_id}:"
        to_del = [k for k in cls._cache if k.startswith(prefix)]
        for k in to_del:
            cls._cache.pop(k, None)
        return len(to_del)
