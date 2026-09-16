# HR Analytics AI Report Builder — API Specification

The REST API is built with FastAPI and provides endpoints for authentication, natural language query processing, SQL explanation, policy RAG, analytics, and automated report generation.

Interactive Swagger UI documentation is available at `http://localhost:8000/docs`.

---

## 1. Authentication (`/api/auth`)

### `POST /api/auth/login`
Authenticates a user and returns a signed JWT access token.
- **Request Body**:
  ```json
  {
    "username": "admin",
    "password": "admin123"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user_id": 1,
    "username": "admin",
    "full_name": "System Administrator",
    "role": "admin",
    "department_id": null
  }
  ```

### `GET /api/auth/me`
Returns details of the currently authenticated user.

---

## 2. Natural Language Query & SQL Explainer (`/api/query`)

### `POST /api/query/ask`
Converts a natural language business question into validated SQL, executes it against the database, masks PII based on role, and returns results with an executive explanation.
- **Request Body**:
  ```json
  {
    "query": "Show employee attrition by department in 2026"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "natural_query": "Show employee attrition by department in 2026",
    "sql": "SELECT d.name AS department_name, ... FROM departments d JOIN employees e ...",
    "matched_template": "Annualized Voluntary & Involuntary Attrition Rates",
    "explanation": "### Executive Summary & Business Explanation...",
    "columns": ["department_name", "active_employees", "voluntary_exits", "turnover_pct"],
    "data": [...],
    "row_count": 7,
    "execution_time_ms": 14.5
  }
  ```

### `POST /api/query/explain`
Explains a complex SQL query in plain English for business users.
- **Request Body**:
  ```json
  {
    "sql": "SELECT d.name, AVG(c.base_salary) FROM departments d JOIN employees e ON d.id = e.department_id JOIN compensation_history c ON e.id = c.employee_id WHERE e.status = 'Active' GROUP BY d.name;"
  }
  ```

---

## 3. Enterprise SQL Repository (`/api/sql-repo`)

### `GET /api/sql-repo/`
Lists all verified historical SQL reports in the catalog. Filterable by `?category=Attrition`.

### `POST /api/sql-repo/search`
Vector semantic search across enterprise SQL templates.
- **Request Body**:
  ```json
  {
    "query": "compa-ratio and compensation equity",
    "top_k": 3
  }
  ```

---

## 4. Policy RAG (`/api/rag`)

### `POST /api/rag/ask`
Answers HR policy questions with citations from internal handbooks.
- **Request Body**:
  ```json
  {
    "question": "What is our remote work home office stipend?"
  }
  ```

---

## 5. Reports & Exports (`/api/reports`)

### `POST /api/reports/generate`
Assembles a complete report structure with KPIs, AI strategic briefing, and tabular results.

### `POST /api/reports/export/pdf`
Generates and downloads a corporate PDF document formatted via ReportLab.

### `POST /api/reports/export/excel`
Generates and downloads a multi-tab formatted Excel workbook formatted via openpyxl.

---

## 6. Module 1: Database & Schema (`/api/database`)

### `GET /api/database/list`
Safe listing of registered databases without exposing connection credentials.

### `POST /api/database/test`
Tests reachability and authentication without persisting state.
- **Request Body**:
  ```json
  {
    "db_type": "postgresql",
    "connection_url": "postgresql://user:pass@localhost:5432/hr_dw"
  }
  ```

### `GET /api/database/schema/{database_id}`
Returns discovered schema metadata JSON, table allowlists, and SHA-256 schema hash.
