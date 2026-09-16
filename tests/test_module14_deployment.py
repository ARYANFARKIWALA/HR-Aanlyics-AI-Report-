"""Unit and Integration Tests for Module 14 — Deployment & Production Setup."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from config.settings import AppSettings
from scripts.backup_db import backup_database
from scripts.restore_db import restore_database


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_settings_configuration_and_validation():
    """Test 1: AppSettings correctly initializes, identifies environments, and validates startup."""
    # Test dev settings
    dev_settings = AppSettings(environment="development")
    assert dev_settings.is_production() is False
    assert dev_settings.api_port == 8000
    assert dev_settings.frontend_port == 8501

    # Test production validation catches default insecure secrets
    prod_insecure = AppSettings(
        environment="production",
        jwt_secret="change_in_production_key"
    )
    issues = prod_insecure.validate_for_startup()
    assert any("Insecure JWT secret" in issue for issue in issues)

    # Test valid production configuration
    prod_secure = AppSettings(
        environment="production",
        jwt_secret="a_very_secure_random_key_that_exceeds_32_characters_length",
        database_url="postgresql://user:pass@localhost:5432/db",
        cors_origins=["https://hr-reports.company.com"]
    )
    prod_issues = prod_secure.validate_for_startup()
    assert len(prod_issues) == 0


def test_health_and_readiness_endpoints(client):
    """Test 2: Liveness (/health) and Readiness (/ready) probes return valid status."""
    # 1. Liveness check
    h_resp = client.get("/health")
    assert h_resp.status_code == 200
    h_data = h_resp.json()
    assert h_data["status"] == "healthy"
    assert h_data["version"] == "2.0.0"
    assert h_data["database"] == "connected"

    # 2. Readiness check
    r_resp = client.get("/ready")
    assert r_resp.status_code == 200
    r_data = r_resp.json()
    assert r_data["status"] == "ready"
    deps = r_data["dependencies"]
    assert deps["metadata_database"] == "ok"
    assert deps["connection_manager"] == "ok"
    assert deps["registered_databases"] >= 1


def test_backup_and_restore_cycle():
    """Test 3: Backup script creates verified archive and restore script restores data integrity."""
    with tempfile.TemporaryDirectory() as tmp_backup_dir:
        # 1. Create backup
        manifest = backup_database(backup_folder=tmp_backup_dir, retention_count=5)
        assert manifest["status"] == "VERIFIED"
        assert manifest["backup_file"].endswith(".bak.gz")
        assert os.path.exists(os.path.join(tmp_backup_dir, manifest["backup_file"]))

        # 2. Restore backup to temporary target file
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_target:
            target_path = tmp_target.name

        try:
            restore_result = restore_database(
                backup_file=manifest["backup_file"],
                target_restore_path=target_path,
                backup_folder=tmp_backup_dir
            )
            assert restore_result["status"] == "RESTORE_SUCCESSFUL"
            assert restore_result["verified_employees"] > 0
            assert restore_result["verified_departments"] > 0
        finally:
            if os.path.exists(target_path):
                os.remove(target_path)
            old_file = target_path + ".old"
            if os.path.exists(old_file):
                os.remove(old_file)


def test_dockerfile_and_compose_configuration():
    """Test 4: Dockerfile and docker-compose.yml contain hardened non-root and multi-service specs."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dockerfile_path = os.path.join(project_root, "Dockerfile")
    compose_path = os.path.join(project_root, "docker-compose.yml")

    assert os.path.exists(dockerfile_path)
    assert os.path.exists(compose_path)

    with open(dockerfile_path, "r", encoding="utf-8") as f:
        df_content = f.read()

    # Verify security hardening in Dockerfile
    assert "USER appuser" in df_content
    assert "HEALTHCHECK" in df_content
    assert "EXPOSE 8000 8501" in df_content

    with open(compose_path, "r", encoding="utf-8") as f:
        compose_content = f.read()

    # Verify 4 production services in compose
    assert "nginx:" in compose_content
    assert "app:" in compose_content
    assert "postgres:" in compose_content
    assert "redis:" in compose_content


def test_nginx_reverse_proxy_configuration():
    """Test 5: Nginx configuration enforces TLS, security headers, rate limiting, and proxy routes."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nginx_conf_path = os.path.join(project_root, "nginx", "nginx.conf")

    assert os.path.exists(nginx_conf_path)

    with open(nginx_conf_path, "r", encoding="utf-8") as f:
        conf = f.read()

    # Verify TLS and redirection
    assert "listen 443 ssl;" in conf
    assert "return 301 https://" in conf

    # Verify security headers
    assert "Strict-Transport-Security" in conf
    assert "X-Content-Type-Options \"nosniff\"" in conf
    assert "X-Frame-Options \"SAMEORIGIN\"" in conf
    assert "Referrer-Policy" in conf

    # Verify rate limiting and proxying
    assert "limit_req_zone" in conf
    assert "fastapi_backend" in conf
    assert "streamlit_frontend" in conf
