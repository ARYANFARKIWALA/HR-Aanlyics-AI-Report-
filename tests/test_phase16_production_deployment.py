"""Comprehensive Unit and Integration Tests for Phase 16 — Production Deployment."""

import os
import re
import pytest
from config.settings import AppSettings
from config.production import ProductionConfiguration, ProductionConfigError
from scripts.backup_db import backup_database
from scripts.restore_db import restore_database


def test_env_example_completeness_and_zero_hardcoded_secrets():
    """Verify that .env.example exists and contains no active secrets."""
    env_example_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.example")
    assert os.path.exists(env_example_path), ".env.example must be present"

    with open(env_example_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_keys = [
        "APP_ENV",
        "SECRET_KEY",
        "DATABASE_URL",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "REDIS_URL",
        "QUERY_TIMEOUT_SECONDS",
        "MAX_QUERY_ROW_LIMIT",
        "ENFORCE_READ_ONLY"
    ]
    for key in required_keys:
        assert f"{key}=" in content, f"Missing key '{key}' in .env.example"

    # Verify no raw production secrets are hardcoded
    assert "hr_app_secure_pass_2026" not in content


def test_docker_compose_security_and_services():
    """Verify docker-compose.yml defines all services with healthchecks and zero hardcoded credentials."""
    compose_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml")
    assert os.path.exists(compose_path)

    with open(compose_path, "r", encoding="utf-8") as f:
        compose_content = f.read()

    required_services = ["nginx", "backend", "frontend", "postgres", "redis"]
    for svc in required_services:
        assert f"{svc}:" in compose_content, f"Service '{svc}' missing from docker-compose.yml"

    # Verify healthchecks are defined
    assert "healthcheck:" in compose_content
    assert "pg_isready" in compose_content

    # Verify zero hardcoded plaintext passwords in postgres or backend environment
    assert "POSTGRES_PASSWORD: hr_app_secure_pass" not in compose_content
    assert "${POSTGRES_PASSWORD}" in compose_content or "${POSTGRES_PASSWORD:" in compose_content


def test_dockerfile_security_hardening():
    """Verify Dockerfile enforces non-root execution and security best practices."""
    dockerfile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Dockerfile")
    assert os.path.exists(dockerfile_path)

    with open(dockerfile_path, "r", encoding="utf-8") as f:
        df_content = f.read()

    assert "USER appuser" in df_content, "Container must execute under non-root user"
    assert "HEALTHCHECK" in df_content, "Container must define HEALTHCHECK probe"
    assert "EXPOSE" in df_content


def test_production_config_fail_fast_validation():
    """Verify ProductionConfiguration raises errors on insecure settings in production mode."""
    insecure_settings = AppSettings(
        environment="production",
        jwt_secret="change_in_production_secret_key_12345",
        database_url="sqlite:///./insecure.db",
        enforce_read_only=True
    )

    with pytest.raises(ProductionConfigError) as exc:
        ProductionConfiguration.validate_production_invariants(insecure_settings)

    error_msg = str(exc.value)
    assert "JWT secret" in error_msg
    assert "SQLite is prohibited" in error_msg


def test_database_backup_and_restore_cycle(tmp_path):
    """Verify backup creation with SHA-256 and restore cycle on real database."""
    source_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hr_analytics.db")
    backup_dir = tmp_path / "backups"

    manifest = backup_database(
        source_db_path=str(source_db),
        backup_folder=str(backup_dir),
        retention_count=5
    )

    backup_filepath = os.path.join(str(backup_dir), manifest["backup_file"])
    assert os.path.exists(backup_filepath)
    assert manifest["source_sha256"] is not None
    assert manifest["backup_sha256"] is not None

    # Test restore
    target_restore_path = tmp_path / "restored_db.sqlite"
    restore_manifest = restore_database(
        backup_file=manifest["backup_file"],
        target_restore_path=str(target_restore_path),
        backup_folder=str(backup_dir)
    )

    assert os.path.exists(target_restore_path)
    assert restore_manifest["restored_sha256"] == manifest["source_sha256"]
