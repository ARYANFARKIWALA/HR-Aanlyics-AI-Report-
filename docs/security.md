# Security Architecture & Data Governance

## 1. Zero-Trust SQL Validator Gate (Module 7)

Every SQL query submitted for execution undergoes AST (Abstract Syntax Tree) parsing using SQLGlot:
- **Statement Whitelist**: Only single `SELECT` or `WITH ... SELECT` queries are permitted.
- **Blocked Mutations**: `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE` trigger immediate blocking.
- **Chained Query Defense**: Semicolons terminating or stacking statements are rejected.
- **Function Allowlist**: Only safe aggregation and mathematical functions (`count`, `sum`, `avg`, `round`, `coalesce`, etc.) are permitted.
- **Credential Protection**: Columns referencing passwords, hashes, keys, or secrets (`hashed_password`, `password`, `token`, `secret`) are blocked with a blocker violation.
- **Cartesian Join Defense**: Unbounded cross joins are detected and flagged.

---

## 2. Authentication & Session Security (Module 11)

- **PBKDF2 HMAC-SHA256**: 100,000 iterations with 16-byte random salts per user.
- **Session Expiration**: 30-minute idle session timeout with token invalidation upon logout.
- **Brute-Force Lockout**: 5 failed login attempts trigger an automatic 15-minute account lock.

---

## 3. Column-Level Security (CLS) & Masking

When datasets are retrieved or exported:
- Users with `pii:view_unmasked` clearance see raw fields.
- Non-privileged roles (`hr_analyst`, `viewer`) receive automatically masked data:
  - **Email**: `sa***@company.com`
  - **Phone**: `***-***-1234`
  - **Salary**: Partial range or redacted `[CONFIDENTIAL]`
  - **SSN**: Masked `***-**-6789`
