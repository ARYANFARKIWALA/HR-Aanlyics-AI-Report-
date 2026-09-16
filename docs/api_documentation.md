# REST API Reference Documentation

The **HR Analytics AI Report Builder** provides a comprehensive FastAPI REST API documented with interactive Swagger/OpenAPI at `http://localhost:8000/docs`.

---

## 1. Authentication Endpoints

### `POST /api/auth/login`
Authenticates a user and issues an HMAC-SHA256 JWT access token.
- **Request**:
  ```json
  {
    "username": "admin",
    "password": "YourPassword123!"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "role": "SUPER_ADMIN",
    "expires_in_minutes": 480
  }
  ```

### `POST /api/auth/logout`
Terminates the user session and logs an audit logout event.

---

## 2. Text-to-SQL & Query Generation

### `POST /api/text-to-sql/generate`
Translates natural language to dialect-specific SQL. **Never executes SQL**.
- **Request**:
  ```json
  {
    "query": "Show monthly employee attrition by department for 2026.",
    "database_id": "sqlite_hr_default",
    "user_role": "SUPER_ADMIN"
  }
  ```
- **Response**:
  ```json
  {
    "status": "SUCCESS",
    "sql": "SELECT d.name as department, strftime('%Y-%m', e.termination_date) as month, COUNT(e.id) as terminations FROM employees e JOIN departments d ON e.department_id = d.id WHERE e.status = 'Terminated' GROUP BY d.name, month;",
    "dialect": "sqlite",
    "confidence_score": 0.95,
    "execution_permitted": false
  }
  ```

---

## 3. SQL Validation & Security Gate

### `POST /api/sql-validator/validate`
Validates SQL syntax, inspects AST, checks allowlists, and enforces zero mutations.
- **Request**:
  ```json
  {
    "sql": "SELECT d.name, COUNT(e.id) FROM employees e JOIN departments d ON e.department_id = d.id GROUP BY d.name;",
    "database_id": "sqlite_hr_default"
  }
  ```
- **Response**:
  ```json
  {
    "status": "APPROVED",
    "validation_id": "val_11cd72637f7d4a95be49b880fc8d9849",
    "risk_score": 12.0,
    "is_valid": true,
    "can_execute": true,
    "max_row_limit": 5000,
    "timeout_seconds": 30
  }
  ```

---

## 4. Secure Query Execution

### `POST /api/query-execution/execute`
Executes an approved query using a validation token from Module 7.
- **Request**:
  ```json
  {
    "validation_id": "val_11cd72637f7d4a95be49b880fc8d9849",
    "bypass_cache": false
  }
  ```
- **Response**:
  ```json
  {
    "status": "SUCCESS",
    "execution_id": "exec_5a9b1c2d",
    "columns": ["name", "attrition_count"],
    "rows": [{"name": "Engineering", "attrition_count": 2}],
    "row_count": 1,
    "execution_time_ms": 14.5
  }
  ```

---

## 5. Report Building & Export

### `POST /api/reports/generate`
Executes end-to-end 7-stage report generation from a natural language question.
- **Export formats**:
  - `GET /api/reports/{id}/export/csv`
  - `GET /api/reports/{id}/export/excel`
  - `GET /api/reports/{id}/export/pdf`
