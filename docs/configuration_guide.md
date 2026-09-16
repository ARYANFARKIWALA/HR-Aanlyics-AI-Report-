# Production Configuration Guide

This guide details all configuration options, environment variables, security guardrails, and runtime parameters of the **HR Analytics AI Report Builder**.

---

## 1. Environment Variable Reference

All configuration keys are defined in `.env` and loaded via Pydantic settings (`config/settings.py` and `config/production.py`).

| Variable Name | Required | Default Value | Description |
|---|---|---|---|
| `APP_ENV` | Yes | `production` | Environment mode (`development`, `staging`, `production`, `testing`). In `production`, strict security invariants are enforced. |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). In production, logs output as structured JSON. |
| `API_HOST` | No | `0.0.0.0` | Host interface for FastAPI backend server. |
| `API_PORT` | No | `8000` | Port for FastAPI backend service. |
| `FRONTEND_PORT` | No | `8501` | Port for Streamlit executive UI. |
| `SECRET_KEY` | Yes | None | 256-bit secret key used to sign JWT session tokens. Must be generated via `openssl rand -hex 32`. |
| `ALGORITHM` | No | `HS256` | Cryptographic algorithm for JWT signature. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `480` | JWT token validity window (default 8 hours). |
| `DATABASE_URL` | Yes | None | SQLAlchemy connection string for metadata database (PostgreSQL in production). |
| `ENCRYPTION_MASTER_KEY` | Yes | None | AES-256 GCM key used to encrypt target database passwords at rest. |
| `QUERY_TIMEOUT_SECONDS` | No | `30` | Maximum execution time in seconds before query execution is terminated. |
| `MAX_QUERY_ROW_LIMIT` | No | `5000` | Maximum rows returned by any query to prevent client memory exhaustion. |
| `ENFORCE_READ_ONLY` | Yes | `True` | Invariant enforcing read-only driver connections. Cannot be disabled in production. |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Connection URL for Redis query caching and rate limiting. |
| `DEFAULT_LLM_PROVIDER` | No | `gemini` | AI model provider (`gemini` or `openai`). |
| `LLM_MODEL` | No | `gemini-1.5-pro` | Model version for Text-to-SQL query planning. |
| `GEMINI_API_KEY` | Conditional | None | Google Cloud Gemini API key for AI query planning. |
| `OPENAI_API_KEY` | Conditional | None | OpenAI API key if using OpenAI provider. |

---

## 2. Production Fail-Fast Validation Invariants

When `APP_ENV=production`, `ProductionConfiguration.validate_production_invariants()` automatically executes during startup:
1. **JWT Secret Invariance**: Rejects default secrets (`change_in_production`, `secret`, `123456`) or keys shorter than 32 characters.
2. **PostgreSQL Invariance**: Rejects `sqlite:///` database URLs. Enterprise PostgreSQL is mandatory for concurrent multi-user metadata storage.
3. **Read-Only Invariance**: Rejects configuration if `ENFORCE_READ_ONLY` is set to `False`.
4. **Credential Exfiltration Invariance**: Verifies all logging outputs pass through `AuditDataSanitizer` to scrub sensitive attributes.

---

## 3. Rate Limiting & Proxy Configuration

In `nginx/nginx.conf`:
- Authentication endpoints (`/api/auth/login`) are protected by a rate limit of 10 requests per minute per IP address.
- All non-TLS HTTP requests on port 80 are redirected to HTTPS on port 443 with HSTS (`Strict-Transport-Security`).
