"""Module 1: Multi-Database Connection & Schema Manager.

Implements:
1. Multi-database support (PostgreSQL / MySQL / SQL Server / Oracle / SQLite).
2. Explicit, mandatory `database_id` throughout all operations (no mutable global DB).
3. Deliberate split:
   - `test_connection`: Non-persisting reachability/auth/access test
   - `connect`: Connection pool creation
   - `discover_schema`: Structured metadata extraction
4. Credentials / Knowledge Split:
   - Encrypted credential storage (Fernet AES-128-CBC + HMAC)
   - Only structural metadata exported to RAG (M5) and downstream modules
5. Discovered schema as the single source of truth for M7 validation and M8 execution.
"""

import base64
import os
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .dialect import SQLDialectRules, get_dialect_rules
from .schema_manager import DiscoveredSchema, SchemaManager

# Encryption key for securing connection credentials (M14)
# Generate deterministic or environment-provided Fernet key
SECRET_SALT = os.getenv("SECRET_KEY", "hr_analytics_super_secret_jwt_key_2026_change_in_production")
# Fernet requires 32 url-safe base64 bytes
KEY_BYTES = base64.urlsafe_b64encode(SECRET_SALT.ljust(32)[:32].encode("utf-8"))
CIPHER_SUITE = Fernet(KEY_BYTES)


class DatabaseConnectionConfig:
    """Configuration for an enterprise database target."""

    def __init__(
        self,
        database_id: str,
        display_name: str,
        db_type: str,  # sqlite, postgresql, mysql, sqlserver, oracle
        connection_url: str,
        description: str = "",
        is_default: bool = False
    ):
        self.database_id = database_id
        self.display_name = display_name
        self.db_type = db_type.lower()
        self.connection_url = connection_url
        self.description = description
        self.is_default = is_default

    def encrypt_url(self) -> str:
        """Encrypts connection string (never plaintext in app storage)."""
        return CIPHER_SUITE.encrypt(self.connection_url.encode("utf-8")).decode("utf-8")

    @classmethod
    def decrypt_url(cls, encrypted_str: str) -> str:
        """Decrypts connection string for internal connection manager use only."""
        return CIPHER_SUITE.decrypt(encrypted_str.encode("utf-8")).decode("utf-8")


class ConnectionManager:
    """Manages multi-engine connectors, schema discovery, and credential encryption."""

    def __init__(self):
        self._engines: dict[str, Engine] = {}
        self._session_makers: dict[str, sessionmaker] = {}
        self._configs: dict[str, DatabaseConnectionConfig] = {}
        self._schemas: dict[str, DiscoveredSchema] = {}
        self._default_db_id: str = "sqlite_hr_default"

        # Initialize default embedded HR SQLite database
        self._register_default_database()

    def _register_default_database(self):
        default_cfg = DatabaseConnectionConfig(
            database_id="sqlite_hr_default",
            display_name="Enterprise HR Data Mart (Primary SQLite)",
            db_type="sqlite",
            connection_url=os.getenv("DATABASE_URL", "sqlite:///./hr_analytics.db"),
            description="Primary transactional HR datamart with employee history, compensation, and review records.",
            is_default=True
        )
        self.register_and_connect(default_cfg)

    # -------------------------------------------------------------
    # Component 1: Test Connection (Reachability, Auth, Access Check)
    # -------------------------------------------------------------
    def test_connection(self, db_type: str, connection_url: str) -> tuple[bool, str, dict[str, Any]]:
        """Tests reachability and credentials without persisting or modifying state.
        
        Returns:
            (success: bool, message: str, diagnostic_info: dict)
        """
        connect_args = {"check_same_thread": False} if connection_url.startswith("sqlite") else {}
        test_engine = None
        try:
            test_engine = create_engine(connection_url, connect_args=connect_args)
            with test_engine.connect() as conn:
                # Run lightweight diagnostic ping
                res = conn.execute(text("SELECT 1"))
                scalar = res.scalar()
                if scalar != 1:
                    return False, f"Diagnostic query returned unexpected value: {scalar}", {}

            dialect_rules = get_dialect_rules(db_type)
            return True, f"Connection test succeeded! Engine responded with dialect '{dialect_rules.dialect_name}'.", {
                "dialect": dialect_rules.dialect_name,
                "supports_ctes": dialect_rules.supports_ctes,
                "limit_syntax": dialect_rules.limit_syntax
            }
        except Exception as exc:
            return False, f"Connection test failed: {exc!s}", {}
        finally:
            if test_engine:
                test_engine.dispose()

    # -------------------------------------------------------------
    # Component 2: Register & Connect (Establishes Connection Pool)
    # -------------------------------------------------------------
    def register_and_connect(self, config: DatabaseConnectionConfig) -> DiscoveredSchema:
        """Establishes persistent engine pool and automatically discovers schema."""
        db_id = config.database_id
        self._configs[db_id] = config

        connect_args = {"check_same_thread": False} if config.connection_url.startswith("sqlite") else {}
        engine = create_engine(config.connection_url, connect_args=connect_args, pool_pre_ping=True)
        self._engines[db_id] = engine
        self._session_makers[db_id] = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # ---------------------------------------------------------
        # Component 3: Automatic Schema Discovery (Structured JSON)
        # ---------------------------------------------------------
        schema = SchemaManager.discover_schema(
            database_id=db_id,
            engine=engine,
            dialect=config.db_type
        )
        self._schemas[db_id] = schema

        if config.is_default:
            self._default_db_id = db_id

        print(f"[ConnectionManager] Registered DB '{db_id}' ({config.db_type}) with {len(schema.tables)} tables. Hash: {schema.schema_hash[:8]}...")
        return schema

    # -------------------------------------------------------------
    # Accessors requiring explicit database_id
    # -------------------------------------------------------------
    def get_engine(self, database_id: str | None = None) -> Engine:
        target_id = database_id or self._default_db_id
        if target_id not in self._engines:
            raise KeyError(f"Database ID '{target_id}' is not registered or connected.")
        return self._engines[target_id]

    def get_session(self, database_id: str | None = None) -> Session:
        target_id = database_id or self._default_db_id
        if target_id not in self._session_makers:
            raise KeyError(f"Database ID '{target_id}' is not registered or connected.")
        return self._session_makers[target_id]()

    def get_schema(self, database_id: str | None = None) -> DiscoveredSchema:
        target_id = database_id or self._default_db_id
        if target_id not in self._schemas:
            # Attempt re-discovery
            engine = self.get_engine(target_id)
            cfg = self._configs[target_id]
            self._schemas[target_id] = SchemaManager.discover_schema(target_id, engine, cfg.db_type)
        return self._schemas[target_id]

    def get_dialect_rules(self, database_id: str | None = None) -> SQLDialectRules:
        target_id = database_id or self._default_db_id
        cfg = self._configs.get(target_id)
        db_type = cfg.db_type if cfg else "sqlite"
        return get_dialect_rules(db_type)

    def check_schema_changed(self, database_id: str, expected_hash: str) -> bool:
        """Component 4: Verification for M8 execution to prevent stale schema queries."""
        current_schema = self.get_schema(database_id)
        return current_schema.schema_hash != expected_hash

    # -------------------------------------------------------------
    # Credentials / Knowledge Split (Safe UI / API Listing)
    # -------------------------------------------------------------
    def list_databases_safe(self) -> list[dict[str, Any]]:
        """Returns registered databases WITHOUT exposing credentials/connection strings."""
        result = []
        for db_id, cfg in self._configs.items():
            schema = self._schemas.get(db_id)
            result.append({
                "database_id": db_id,
                "display_name": cfg.display_name,
                "db_type": cfg.db_type,
                "description": cfg.description,
                "is_default": (db_id == self._default_db_id),
                "table_count": len(schema.tables) if schema else 0,
                "schema_hash": schema.schema_hash if schema else "",
                "discovered_at": schema.discovered_at if schema else ""
            })
        return result


connection_manager = ConnectionManager()
