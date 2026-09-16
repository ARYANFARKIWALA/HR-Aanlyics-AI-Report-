# Production Troubleshooting & FAQ Guide

This guide covers common operational issues, diagnostics, error codes, and resolution steps for the **HR Analytics AI Report Builder**.

---

## 1. Common Issues & Resolutions

### Issue 1: `ProductionConfigError: Insecure JWT secret key`
- **Cause**: `APP_ENV=production` is active and `SECRET_KEY` in `.env` is either using default placeholder text or is shorter than 32 characters.
- **Resolution**: Generate a secure 256-bit random key using `openssl rand -hex 32` and assign it to `SECRET_KEY` in `.env`.

### Issue 2: `Schema hallucination: Table(s) [...] do not exist in database`
- **Cause**: The generated or input query referenced tables outside the verified database catalog allowlist.
- **Resolution**: Verify the database registration in `ConnectionManager`. If a new table was added to the database, re-run schema discovery via `POST /api/databases/{id}/sync-schema`.

### Issue 3: `Security Violation: Access to sensitive field 'ssn' is strictly blocked`
- **Cause**: A query attempted to select restricted PII or credential fields.
- **Resolution**: This is by design. Module 7 strictly protects employee privacy and credential tables. Use pre-approved aggregate views instead of selecting raw PII.

### Issue 4: `Query execution timeout exceeded`
- **Cause**: A query took longer than the configured timeout window (`QUERY_TIMEOUT_SECONDS=30`).
- **Resolution**: Inspect the query execution plan in the query history. Ensure proper indexes exist on joined columns (`department_id`, `job_profile_id`, `termination_date`).

### Issue 5: Streamlit WebSocket Disconnection
- **Cause**: Nginx proxy dropped the persistent WebSocket connection to port 8501.
- **Resolution**: Verify `nginx/nginx.conf` includes WebSocket upgrade headers:
  ```nginx
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  ```

---

## 2. Health Check Diagnostics

- Check backend liveness:
  ```bash
  curl -i http://localhost:8000/health
  ```
- Check backend readiness:
  ```bash
  curl -i http://localhost:8000/ready
  ```
- Check frontend health:
  ```bash
  curl -i http://localhost:8501/_stcore/health
  ```
