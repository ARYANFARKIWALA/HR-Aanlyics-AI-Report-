"""Phase 16: Production Configuration & Enterprise Hardening.

Enforces zero-default-secrets, fail-fast validation in production mode,
and structured logging configuration.
"""

import os
import sys
import logging
import json
from typing import Dict, Any, List, Optional
from config.settings import AppSettings, EnvironmentType


class ProductionConfigError(Exception):
    """Raised when critical production secrets or configurations are absent."""
    pass


class ProductionConfiguration:
    """Production deployment validator and configuration provider."""

    @staticmethod
    def get_settings() -> AppSettings:
        """Loads and strictly validates settings for deployment."""
        settings = AppSettings()
        ProductionConfiguration.validate_production_invariants(settings)
        return settings

    @staticmethod
    def validate_production_invariants(settings: AppSettings):
        """Enforces zero-trust production security invariants."""
        if not settings.is_production():
            return

        violations = []

        # 1. Reject placeholder or default secret keys
        insecure_keys = [
            "replace_with",
            "change_in_production",
            "secret",
            "123456",
            "password"
        ]
        if any(bad in settings.jwt_secret.lower() for bad in insecure_keys) or len(settings.jwt_secret) < 32:
            violations.append("CRITICAL: Insecure or default JWT secret key detected. Production requires random 64-char key.")

        # 2. SQLite prohibited as production database
        if settings.database_url.startswith("sqlite"):
            violations.append("CRITICAL: SQLite is prohibited for production deployment. Enterprise PostgreSQL required.")

        # 3. Read-only driver enforcement must be active
        if not settings.enforce_read_only:
            violations.append("CRITICAL: Read-only query enforcement must be enabled in production.")

        if violations:
            raise ProductionConfigError("\n".join(violations))

    @staticmethod
    def setup_production_logging(level_name: str = "INFO"):
        """Configures structured JSON logging for container monitoring."""
        log_level = getattr(logging, level_name.upper(), logging.INFO)

        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_entry = {
                    "timestamp": self.formatTime(record, self.datefmt),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "lineno": record.lineno,
                }
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_entry)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())

        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.handlers = [handler]
