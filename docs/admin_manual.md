# Enterprise Administrator Manual

This manual provides administration, security, user management, and maintenance instructions for `SUPER_ADMIN` and `HR_ADMIN` users.

---

## 1. Role-Based Access Control (RBAC) & User Management

The platform enforces 5 canonical roles:

| Role | Database Connect | SQL Upload | Rule Edit | RAG Manage | Report Exec | User Admin |
|---|---|---|---|---|---|---|
| `SUPER_ADMIN` | YES | YES | YES | YES | YES | YES |
| `HR_ADMIN` | YES | YES | YES | YES | YES | NO |
| `HR_MANAGER` | Select only | NO | View only | NO | YES | NO |
| `ANALYST` | Select only | YES | View only | NO | YES | NO |
| `REPORT_VIEWER`| Select only | NO | NO | NO | View only | NO |

### Creating and Modifying Users
Administrators can provision users through the **Administration** tab or the API (`POST /api/auth/users`). Passwords must meet enterprise complexity requirements (12+ characters, uppercase, lowercase, numbers, and symbols) and are hashed with PBKDF2 with unique salts. Account lockout is triggered after 5 consecutive failed attempts for 15 minutes.

---

## 2. Managing the SQL Repository & Institutional Knowledge

Under **SQL Repository**:
1. Review approved organizational SQL reports.
2. Upload verified HR queries with their join graphs, business explanations, and effective-dating policies.
3. The platform automatically indexes uploaded queries into the RAG vector store for instant retrieval by the Text-to-SQL engine.

---

## 3. Business Rules Management

Under **Business Rules**:
- Create and approve formal organizational definitions (e.g. *Active Status Definition*, *Voluntary Attrition Policy*, *Compa-Ratio Thresholds*).
- Rules require review and approval by an `HR_ADMIN`.
- When an active rule is modified, an immutable version snapshot is created for auditing.

---

## 4. Monitoring & Audit Dashboard

Under **Administration $\rightarrow$ Monitoring**:
Track real-time system KPIs:
- Total AI requests & queries executed.
- SQL validation success rate and rejection rate.
- Average response latency and execution latency.
- RAG retrieval latency and hit rate.
- Security violation attempts and blocked adversarial queries.
- Audit event explorer recording all 13 required platform lifecycle events.
