# HR Analytics AI Report Builder
## Complete Enterprise Intelligence Platform (Modules 1 through 14)

[![CI/CD Pipeline](https://github.com/organization/hr-ai-report-builder/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/organization/hr-ai-report-builder/actions)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Enterprise-green.svg)](LICENSE)
[![Test Coverage](https://img.shields.io/badge/tests-138%20passed-brightgreen.svg)](tests/)

> **Converts enterprise HR SQL reporting knowledge into an intelligent, secure natural-language reporting assistant.**

Organizations maintain hundreds of complex HR SQL reports developed over decades. These queries feature intricate join graphs, effective-dating logic (`effective_start_date` / `effective_end_date`), compliance rules, and security filters. The **HR Analytics AI Report Builder** ingests and catalogs this institutional knowledge, allowing business users to ask natural language questions, adapt verified queries without hallucination, understand query logic in plain English, and export boardroom-ready reports in CSV, multi-tab Excel, and executive PDF formats.

---

## 🏛️ End-to-End System Architecture

```text
                                 USERS / HR ANALYSTS
                                          │
                                          ▼
                                     HTTPS / TLS
                                          │
                                          ▼
                          NGINX REVERSE PROXY (PORT 443)
                      Rate Limiting | Security Headers | TLS
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   │                                             │
                   ▼                                             ▼
          STREAMLIT UI (8501)                           FASTAPI BACKEND (8000)
    Interactive Visual Dashboards                   REST API & Security Controllers
                   │                                             │
                   └──────────────────────┬──────────────────────┘
                                          │
                                          ▼
                         MODULE 11: AUTH & AUTHORIZATION
                        PBKDF2 | JWT Sessions | RBAC / ABAC
                                          │
                                          ▼
                         MODULE 5: RAG KNOWLEDGE BASE
                     Schema Context | Business Rules | Vector DB
                                          │
                                          ▼
                         MODULE 6: AI TEXT-TO-SQL ENGINE
                   Query Planning | AST Construction | Dialects
                                          │
                                          ▼
                      MODULE 7: ZERO-TRUST SQL VALIDATOR GATE
                  AST Inspection | Schema Allowlist | Risk Scoring
                                          │ (APPROVED TOKEN)
                                          ▼
                        MODULE 8: QUERY EXECUTION ENGINE
                  Read-Only Connection Pool | Exact Typing | CLS
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   │                                             │
                   ▼                                             ▼
      APPLICATION METADATA DB (PG/SQLite)              AUTHORIZED HR DATABASES
    Users, Roles, Versions, ACLs, Logs             PostgreSQL, MySQL, Oracle, MSSQL
                   │                                             │
                   └──────────────────────┬──────────────────────┘
                                          │
                                          ▼
                          MODULE 9: HR ANALYTICS ENGINE
                 KPIs (Headcount, Turnover) | Outliers | Cohorts
                                          │
                                          ▼
                       MODULE 10: REPORT BUILDER & VISUALS
                        Plotly Charts | KPIs | Multi-Filters
                                          │
                                          ▼
                     MODULE 12: REPORTS LIFECYCLE & EXPORT
                   Versioning | Non-Destructive Restore | ACLs
                       CSV | Multi-Tab Excel | Executive PDF
                                          │
                                          ▼
                     MODULE 13: EVALUATION & QUALITY CONTROL
                   Golden Dataset Benchmarks | Adversarial Gate
                                          │
                                          ▼
                     MODULE 14: DEPLOYMENT & PRODUCTION
                 Docker Containers | Reverse Proxy | Backups
```

---

## 🚀 The 14 Integrated Modules

| # | Module | Core Functionality |
| :--- | :--- | :--- |
| **1** | **Database Connection & Schema** | Multi-engine support (PostgreSQL, MySQL, Oracle, MSSQL, SQLite), credential encryption, and schema allowlists. |
| **2** | **SQL Repository Management** | Centralized query catalog with approval workflows, semantic tagging, and versioning. |
| **3** | **Schema Intelligence** | Automated foreign key graph discovery, human business aliases, and table metrics. |
| **4** | **Business Rule Management** | Formalizes HR business rules into deterministic SQL WHERE filters and temporal dating logic. |
| **5** | **RAG Knowledge Base** | Vector and lexical retrieval grounding queries in HR handbooks, policies, and schemas. |
| **6** | **AI Text-to-SQL Engine** | Multi-dialect query planner that converts natural language to safe, explainable SQL. |
| **7** | **SQL Validator & Security Gate** | Zero-trust AST gatekeeper; blocks mutations, enforces whitelists, and issues cryptographic execution tokens. |
| **8** | **Query Execution Engine** | Validation handshake enforcement, read-only connection pooling, 30s timeouts, and 10k row caps. |
| **9** | **HR Analytics Engine** | Deterministic calculations of turnover rates, compa-ratios, tenure, IQR outliers, and correlations. |
| **10** | **Report Builder & Visualization**| Dynamic Plotly charts (Bar, Line, Donut, Heatmap), KPI cards, and multi-filter slicing. |
| **11** | **Authentication & Authorization**| PBKDF2 password security, 30-min idle timeouts, RBAC, ABAC, and Column-Level Security (CLS) masking. |
| **12** | **Reports Lifecycle & History** | Report CRUD, immutable version history, non-destructive restore, sharing ACLs, and multi-format exports. |
| **13** | **Testing & AI Quality Control**| Golden benchmark evaluation (100% security pass rate) and adversarial penetration stress testing. |
| **14** | **Deployment & Production** | Multi-container Docker Compose, Nginx reverse proxy, TLS, backup/restore scripts, and CI/CD. |

---

## ⚡ Quickstart: Running Locally

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Setup & Installation
```bash
# Clone the repository
git clone https://github.com/organization/hr-ai-report-builder.git
cd hr-ai-report-builder

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # On Windows
# source venv/bin/activate    # On Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Initialize database with rich HR demo dataset
python -m backend.database.seeder
```

### 3. Launch Services
```bash
# Terminal 1: Launch FastAPI Backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Launch Streamlit Dashboard
streamlit run frontend/streamlit_app.py --server.port 8501
```
- **Streamlit Web UI**: `http://localhost:8501`
- **FastAPI Documentation & Swagger UI**: `http://localhost:8000/docs`
- **Liveness Health Check**: `http://localhost:8000/health`
- **Readiness Dependency Probe**: `http://localhost:8000/ready`

---

## 🐳 Docker Deployment

To launch the full production environment with Nginx, PostgreSQL (pgvector), Redis, and the Application:

```bash
docker compose up --build -d
```

---

## 🧪 Testing & Verification

Run the entire system test suite across all 14 modules:

```bash
pytest -v
```

Run the automated AI Quality Control Golden Benchmark:
```bash
python -c "from backend.database.connection import SessionLocal; from evaluation.evaluator import EvaluationEngine; db=SessionLocal(); s=EvaluationEngine.run_benchmark(db); print('Execution Accuracy:', s.execution_accuracy_rate, '% | Security Defense:', s.security_defense_rate, '%')"
```

---

## 🎬 Canonical End-to-End Demonstration

To run the complete 12-stage enterprise demonstration workflow for the canonical question:
> *"Show monthly employee attrition by department for 2026."*

```bash
python scripts/demo_canonical_workflow.py
```

This live script demonstrates:
`Login` $\rightarrow$ `Select Database` $\rightarrow$ `Ask Question` $\rightarrow$ `RAG Retrieval` $\rightarrow$ `Generated SQL` $\rightarrow$ `SQL Validation` $\rightarrow$ `Execution` $\rightarrow$ `Analytics` $\rightarrow$ `Chart` $\rightarrow$ `Report` $\rightarrow$ `Export (CSV/Excel/PDF)` $\rightarrow$ `Audit Log`.

---

## 📚 Documentation Directory

Complete technical specifications and manuals are available in the [`docs/`](docs/) directory:
1. [System Architecture](docs/architecture.md) — Comprehensive end-to-end architecture and data flow.
2. [Module Reference Guide](docs/module_reference.md) — Detailed specifications for all 14 platform layers.
3. [Installation Guide](docs/installation_guide.md) — Local and server installation instructions.
4. [Configuration Guide](docs/configuration_guide.md) — Environment variables, settings, and fail-fast invariants.
5. [Database Setup Guide](docs/database_setup_guide.md) — Multi-engine setup, driver isolation, and backup strategy.
6. [API Documentation](docs/api_documentation.md) — Complete REST API reference and endpoint schemas.
7. [User Manual](docs/user_manual.md) — Guide for HR analysts and business report consumers.
8. [Admin Manual](docs/admin_manual.md) — RBAC administration, SQL catalog curation, and monitoring.
9. [Security Documentation](docs/security_documentation.md) — Zero-trust defense, AST validation, and data masking.
10. [Testing Documentation](docs/testing_documentation.md) — Comprehensive guide to all 9 test categories.
11. [AI Evaluation Report](docs/ai_evaluation_report.md) — Benchmark evaluation across 100+ golden questions.
12. [Deployment Guide](docs/deployment_guide.md) — Containerized deployment, Nginx TLS termination, and operations.
13. [Troubleshooting Guide](docs/troubleshooting_guide.md) — Diagnostics, common issues, and resolution procedures.
14. [Institutional SQL Knowledge Reuse](docs/existing_sql_knowledge_reuse.md) — Why and how existing organizational SQL knowledge is preserved and reused.
