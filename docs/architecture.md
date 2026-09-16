# Complete System Architecture: HR Analytics AI Report Builder
## Modules 1 through 14 Comprehensive Reference

The **HR Analytics AI Report Builder** is an enterprise-grade reporting and analytical intelligence platform that translates natural language inquiries into safe, explainable, and verified SQL queries, grounded in organizational knowledge and business rules.

---

## 1. End-to-End Architectural Diagram

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

## 2. Important Database Separation

The architecture strictly separates **Application Metadata** from **HR Enterprise Data**:

| Domain | Storage Layer | Contents | Security Profile |
| :--- | :--- | :--- | :--- |
| **Application Database** | PostgreSQL / SQLite | Users, credentials (salted hashes), roles, permissions, saved reports, report versions, sharing ACLs, query execution history, security audit logs, RAG vector metadata. | Read/Write for application services; isolated credentials. |
| **HR Enterprise Database** | PostgreSQL, MySQL, Oracle, SQL Server, SQLite | Active employee records, compensation history, departments, performance reviews, leave records, job profiles. | **Strictly Read-Only** user credentials. Mutation statements (DROP, DELETE, UPDATE, ALTER) are permanently blocked. |

---

## 3. The 14-Module Architecture Matrix

1. **Module 1: Database Connection & Schema Management**: Multi-engine connectivity, dialect mappings, credential encryption, and schema allowlists.
2. **Module 2: SQL Repository Management**: Version-controlled query catalog with lifecycle approvals, parameterization, and tags.
3. **Module 3: Schema Intelligence & Metadata**: Semantic table classification, relationship graphs, and usage metrics.
4. **Module 4: Business Rule Management**: Natural language business logic translated into SQL WHERE constraints.
5. **Module 5: RAG Knowledge Base**: Hybrid lexical/vector retrieval over organizational handbooks and schema rules.
6. **Module 6: AI Text-to-SQL Engine**: Query planning, deterministic translation, and plain-English explanation.
7. **Module 7: SQL Validator & Security Gate**: Zero-trust AST gatekeeper that scores risk and signs cryptographic tokens.
8. **Module 8: Query Execution Engine**: Executes strictly approved tokens against read-only connection pools.
9. **Module 9: HR Analytics Engine**: Deterministic calculations of turnover rates, compa-ratios, tenure, and IQR outliers.
10. **Module 10: Report Builder & Visualization**: Interactive Plotly charts, executive KPI cards, and dynamic filter slicing.
11. **Module 11: Authentication & Authorization**: PBKDF2 hashing, 30-minute idle session timeout, RBAC, ABAC, and CLS masking.
12. **Module 12: Reports, Export, Sharing & History**: Report CRUD, version rollback, sharing ACLs, CSV/Excel/PDF exports with CLS.
13. **Module 13: Testing, Evaluation & AI Quality Control**: Golden benchmark dataset, SQL accuracy checks, and adversarial penetration tests.
14. **Module 14: Deployment & Production Setup**: Multi-container Docker compose, Nginx reverse proxy, TLS, backups, and CI/CD.
