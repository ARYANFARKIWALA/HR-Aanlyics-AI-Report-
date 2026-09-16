# Database Setup & Connection Architecture

## 1. Separation of Application Metadata vs HR Reporting Data

Enterprise deployments must maintain strict architectural separation between **Application Metadata** and **HR Reporting Databases**:

```text
[Application Services]
       │
       ├──────────────────────────────────────────┐
       ▼                                          ▼
APPLICATION DATABASE                      HR ENTERPRISE DATABASES
- Users & Sessions                         - PostgreSQL (Workday / SuccessFactors sync)
- Roles & Granular Permissions             - MySQL (Payroll replica)
- Saved Reports & Versions                 - Oracle (Global Core HR)
- Query Execution Audit Logs               - SQL Server (Time & Attendance)
- RAG Documents & Embeddings
```

---

## 2. Read-Only Least-Privilege Provisioning

For HR databases, configure a dedicated `READ_ONLY` database user for reporting:

### PostgreSQL Example
```sql
CREATE USER hr_readonly WITH PASSWORD 'SecureRandomPassword2026!';
GRANT CONNECT ON DATABASE hr_production TO hr_readonly;
GRANT USAGE ON SCHEMA public TO hr_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO hr_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO hr_readonly;
```

### MySQL Example
```sql
CREATE USER 'hr_readonly'@'%' IDENTIFIED BY 'SecureRandomPassword2026!';
GRANT SELECT ON hr_production.* TO 'hr_readonly'@'%';
FLUSH PRIVILEGES;
```

---

## 3. Connection Pooling & Resource Limits

Connection pools are managed by `backend.database.connection_manager.ConnectionManager`:
- **Pool Size**: Default 10 connections per registered database engine.
- **Max Overflow**: 20 overflow connections.
- **Pool Timeout**: 30 seconds.
- **Recycle Time**: 1800 seconds (30 minutes) to eliminate stale connections.
- **Statement Timeout**: Automatically injected per dialect (e.g. `SET statement_timeout = 30000` for Postgres).
