# Configuration Reference: HR Analytics AI Report Builder

All application configuration is managed via typed settings in `config/settings.py` backed by environment variables (`.env`).

---

## Environment Variables Reference

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | string | `development` | Deployment mode: `development`, `testing`, `staging`, `production`. |
| `API_HOST` | string | `0.0.0.0` | Network binding host for FastAPI. |
| `API_PORT` | integer | `8000` | Port for backend REST API. |
| `FRONTEND_PORT` | integer | `8501` | Port for Streamlit dashboard. |
| `DATABASE_URL` | string | `sqlite:///./hr_analytics.db` | Application metadata database connection string. |
| `APP_DATABASE_URL`| string | `None` | Optional separate PostgreSQL metadata database connection string. |
| `HR_DATABASE_URL` | string | `None` | Default registered HR reporting database connection string. |
| `SECRET_KEY` | string | `hr_analytics_super_secret...` | Cryptographic secret for signing JWT session tokens (must be >= 32 chars in production). |
| `ALGORITHM` | string | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | integer | `480` | Duration before JWT session expires (8 hours). |
| `DEFAULT_LLM_PROVIDER` | string | `gemini` | Primary AI provider: `gemini`, `openai`, or `offline`. |
| `LLM_MODEL` | string | `gemini-1.5-flash` | Model identifier for natural language query interpretation. |
| `GEMINI_API_KEY` | string | `None` | Google AI Gemini API secret key. |
| `OPENAI_API_KEY` | string | `None` | OpenAI API key if using GPT models. |
| `MAX_QUERY_ROW_LIMIT` | integer | `10000` | Maximum rows permitted in query execution results to prevent memory exhaustion. |
| `QUERY_TIMEOUT_SECONDS` | integer | `30` | Statement timeout for all read-only SQL queries. |
| `ENFORCE_READ_ONLY`| boolean| `True` | Forces strict validation against data modification statements. |
| `CORS_ORIGINS` | string | `*` | Comma-separated list of allowed CORS client origins. |
| `LOG_LEVEL` | string | `INFO` | Centralized logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

---

## Startup Validation Behavior
When `APP_ENV=production`, the configuration engine validates:
- Insecure default JWT secret keys trigger immediate startup errors.
- SQLite usage logs a high-priority warning recommending PostgreSQL for high concurrency.
- Wildcard CORS (`*`) produces operational security warnings.
