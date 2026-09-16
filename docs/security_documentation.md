# Zero-Trust Security & Compliance Documentation

This document describes the defense-in-depth security model implemented in the **HR Analytics AI Report Builder**.

---

## 1. Zero-Trust Security Architecture

The platform operates on a zero-trust model where every query is treated as untrusted, regardless of user role.

```text
User Request
     │
     ▼
[Layer 1] API Authentication & RBAC Authorization Gate
     │
     ▼
[Layer 2] Text-to-SQL Engine (ZERO EXECUTION PERMITTED)
     │
     ▼
[Layer 3] SQL Validator Gate (AST Parsing, Entity Allowlists, Attack Defense)
     │  --> REJECTED: Returns safe generic explanation
     │  --> APPROVED: Generates single-use execution token
     ▼
[Layer 4] Secure Query Execution (Driver-level Read-Only, Timeout, Row Limit)
     │
     ▼
[Layer 5] Data Redaction & Sensitive Field Masking
     │
     ▼
[Layer 6] Audit Trail Sanitizer (Zero Passwords, Zero Tokens Logged)
```

---

## 2. SQL Injection & Mutation Defense

Module 7 inspects every query using Abstract Syntax Tree (AST) decomposition via SQLGlot:
1. **Mutation Blocking**: Prohibits all non-`SELECT` statements (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`, `EXEC`).
2. **Multi-Statement Defense**: Semicolon-separated statements are strictly blocked.
3. **Cartesian Product Defense**: Unbounded `CROSS JOIN` or non-predicate multi-table joins are blocked to prevent Denial-of-Service (DoS) CPU exhaustion.
4. **Dangerous Function Allowlist**: Prohibits system commands, file I/O, sleep functions, or network calls (`xp_cmdshell`, `pg_sleep`, `benchmark`, `load_file`).

---

## 3. Sensitive Data & Column-Level Security (CLS)

Restricted fields are blocked at the validator layer:
- **Credentials & Hashes**: `password`, `hashed_password`, `token`, `secret`, `salt`.
- **Financial & PII**: `ssn`, `social_security_number`, `bank_account_number`, `routing_number`, `credit_card`.
- **Medical & Health Data**: `medical_history`, `diagnosis`, `health_condition`.

---

## 4. Audit Log Sanitization

`AuditDataSanitizer` scrubs all JSON payloads and error strings before persistence:
- Strips database connection strings with embedded passwords.
- Replaces raw password fields with `[REDACTED]`.
- Enforces strict zero-credential retention across all 13 lifecycle audit events.
