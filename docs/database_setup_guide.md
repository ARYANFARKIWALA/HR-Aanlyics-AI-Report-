# Enterprise Database Setup & Architecture Guide

This guide describes how to configure, connect, and manage multi-engine HR databases within the platform.

---

## 1. Multi-Engine Connection Support

The system supports heterogeneous HR data sources via `ConnectionManager`:
- **PostgreSQL**: `postgresql://user:pass@host:5432/dbname`
- **SQLite**: `sqlite:///path/to/database.db`
- **MySQL**: `mysql+pymysql://user:pass@host:3306/dbname`
- **Microsoft SQL Server**: `mssql+pyodbc://user:pass@host:1433/dbname?driver=ODBC+Driver+18+for+SQL+Server`
- **Oracle**: `oracle+oracledb://user:pass@host:1521/?service_name=hrservice`

### Registering a New Database
Admins can register databases via the API (`POST /api/databases`) or UI. Passwords are never stored in plaintext—they are encrypted at rest using AES-256 GCM (`ENCRYPTION_MASTER_KEY`).

---

## 2. Driver-Level Read-Only Invariant

Module 8 executes queries strictly through read-only driver connections to guarantee zero accidental or malicious data modification:
- **SQLite**: Enforces `PRAGMA query_only = ON;` on every pooled connection.
- **PostgreSQL**: Enforces `SET TRANSACTION READ ONLY;` at connection checkout.
- **MySQL**: Sets `SET SESSION transaction_read_only = 1;`.
- **SQL Server**: Connects using a dedicated SQL user restricted to `db_datareader` role.

---

## 3. Schema Catalog & Entity Allowlists

On database connection, `SchemaManager` performs introspection and builds an allowlist of:
1. **Allowed Tables**: `employees`, `departments`, `job_profiles`, `compensation_history`, `performance_reviews`, `leave_records`.
2. **Allowed Columns**: Exact physical column names and data types.
3. **Column-Level Security (CLS)**: Flags sensitive columns (`ssn`, `bank_account_number`, `hashed_password`) for automatic redaction or blocking.

Any query attempting to query a table or column outside the allowlist is flagged by Module 7 as a schema hallucination and rejected before execution.

---

## 4. Backup & Disaster Recovery Strategy

Automated backup scripts in `scripts/backup_database.py` create compressed GZIP snapshots with SHA-256 checksum verification and configurable retention:
```bash
# Execute snapshot backup
python scripts/backup_database.py

# Restore snapshot to target location
python scripts/restore_database.py --backup-file hr_analytics.db_20260915_211508.bak.gz
```
Manifest records are written to `storage/backups/manifest.json` ensuring full audit traceability.
