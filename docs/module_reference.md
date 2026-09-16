# Complete Module Reference Guide

This document provides a comprehensive technical reference for all 14 functional architectural modules of the **HR Analytics AI Report Builder**.

---

## Architecture Overview Matrix

| Module # | Layer Name | Core Responsibility | Key Invariants & Safeguards | Primary Source Files |
|---|---|---|---|---|
| **Module 1** | Database Connection & Schema Intelligence | Multi-engine connections (PostgreSQL, SQLite, MySQL, SQL Server, Oracle), credential encryption at rest, live schema discovery, catalog allowlist management. | Never exposes raw database credentials. Enforces encrypted storage and per-engine read-only connection pooling. | `backend/database/connection_manager.py`, `backend/database/schema_manager.py` |
| **Module 2** | SQL Repository & Knowledge Ingestion | Institutional HR SQL report catalog, schema lineage tracking, join graph metadata, effective-dating rule extraction. | Preserves existing organizational queries and business definitions rather than hallucinating schemas. | `backend/database/models_repo.py`, `backend/services/sql_repository_service.py` |
| **Module 3** | Schema Intelligence & Semantic Mapping | Business entity resolution, synonym resolution (e.g. headcount $\rightarrow$ active employee count), dialect data type normalization. | Enforces strict schema allowlists for tables and columns. Flags missing or unmapped entities. | `backend/database/schema_intelligence.py` |
| **Module 4** | Business Rules Engine | Centralized catalog of HR definitions (e.g., active employee, voluntary vs involuntary turnover, compa-ratio benchmarks, 9-box performance). | Versioned, immutable rules. Requires admin approval for modifications. | `business_rules/service.py`, `business_rules/validator.py` |
| **Module 5** | Policy RAG & Context Retrieval | Semantic similarity search over approved SQL templates, business rules, and HR policies using vector embeddings. | Combines dense vector retrieval with structured metadata filtering. Rejects conflicting rules. | `rag/rag_service.py`, `rag/retrieval.py` |
| **Module 6** | AI Text-to-SQL Engine | Translates natural language prompts into dialect-adapted SQL queries using RAG context and query planning. | **ZERO EXECUTION PERMITTED**. Anti-hallucination detection. Requests clarification on ambiguous entities. | `text_to_sql/service.py`, `text_to_sql/query_planner.py`, `text_to_sql/safety.py` |
| **Module 7** | SQL Validator & Zero-Trust Security Gate | Abstract Syntax Tree (AST) validation via SQLGlot, dialect checks, Cartesian join prevention, sensitive column masking, row limits. | **ZERO EXECUTION PERMITTED**. Returns `APPROVED` with cryptographic validation token or `REJECTED` with safe explanation. | `sql_validator/service.py`, `sql_validator/security_validator.py` |
| **Module 8** | Secure Query Execution Engine | Executes validated queries against target HR database using driver-level read-only connections (`PRAGMA query_only = ON;`, `SET TRANSACTION READ ONLY;`). | **REQUIRES VALID MODULE 7 TOKEN**. Enforces query timeout (30s) and row limit (5,000). Standardized output `{columns, rows, row_count, execution_time, query_id}`. | `query_execution/service.py`, `query_execution/connection_pool.py` |
| **Module 9** | HR Analytics Engine | Pandas-based reusable calculation services: totals, averages, percentages, ratios, trends, ranking, group analysis, time-series, attrition, headcount, tenure. | Documents all data transformations. Automatically recommends suitable visualizations (Line, Bar, Histogram, Pie, KPI Card). | `analytics/reusable_services.py` |
| **Module 10** | HR Report Builder Pipeline | 7-stage report pipeline (Question $\rightarrow$ Generated SQL $\rightarrow$ Validated SQL $\rightarrow$ Results $\rightarrow$ Analytics $\rightarrow$ Visualization $\rightarrow$ Report). | Preserves 7 mandatory attributes (question, SQL, database, knowledge sources, timestamp, user, report version). Multi-format export (CSV, Excel, PDF). | `report_builder/pipeline_service.py`, `report_builder/exporters/` |
| **Module 11** | Enterprise Streamlit Frontend | Executive UI with 10-section navigation (Dashboard, Ask AI, Reports, SQL Repository, Schema Explorer, Business Rules, RAG, Query History, Admin, Settings). | Clean enterprise interface. Hides technical controls from standard HR users. Displays 7-stage pipeline. | `frontend/app.py`, `frontend/components/` |
| **Module 12** | Authentication & RBAC | Role-Based Access Control (`SUPER_ADMIN`, `HR_ADMIN`, `HR_MANAGER`, `ANALYST`, `REPORT_VIEWER`). Password security (PBKDF2, lockout, length, complexity). | Backend-enforced authorization across all APIs. Session management and credential security. | `backend/auth/authorization.py`, `backend/auth/password.py` |
| **Module 13** | Audit Logging & Operational Monitoring | Real-time logging of 13 lifecycle events. Scrubbing of passwords, credentials, and sensitive HR data. | Dedicated admin monitoring dashboard tracking latency, query volumes, success/rejection rates. | `backend/audit/service.py`, `backend/audit/sanitizer.py`, `backend/audit/metrics_service.py` |
| **Module 14** | Complete End-to-End Orchestrator | Connects all 14 layers into a single cohesive pipeline with zero bypass. | Validates the canonical scenario: *"Show monthly employee attrition by department for 2026."* | `backend/services/workflow_orchestrator.py` |

---

## Detailed Component Specifications

### 1. Zero-Execution Invariant in Modules 6 & 7
Under no circumstances do Module 6 (Text-to-SQL) or Module 7 (SQL Validator) execute SQL queries against any database. Their role is purely analytical, grammatical, and defensive. Module 8 is the sole engine with database execution rights, and it strictly requires an unexpired `APPROVED` validation token issued by Module 7.

### 2. Standardized Query Execution Interface
Module 8 always returns results conforming to the standard schema:
```json
{
  "columns": ["department", "month", "attrition_count"],
  "rows": [
    {"department": "Engineering", "month": "2026-01", "attrition_count": 2},
    {"department": "Sales", "month": "2026-01", "attrition_count": 3}
  ],
  "row_count": 2,
  "execution_time": 12.4,
  "query_id": "exec_8f93e1b092"
}
```

### 3. Preserved Institutional Knowledge
The system preserves 7 critical provenance attributes across all generated and saved reports:
1. **question**: Original natural-language user query.
2. **sql**: Executed dialect-specific SQL query.
3. **database**: Target database identifier.
4. **knowledge_sources**: RAG rules and repository reports used.
5. **timestamp**: ISO 8601 generation timestamp.
6. **user**: Username and role of the report creator.
7. **report_version**: Immutable report revision number.
