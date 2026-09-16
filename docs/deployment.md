# Production Deployment & Operations Guide (Module 14)

This guide provides operational runbooks for deploying, maintaining, backing up, and rolling back the HR Analytics AI platform in production.

---

## 1. Production Deployment Sequence

Deploy in strict sequence:
1. **Application Database**: Start PostgreSQL with pgvector.
2. **Database Migrations / Schema Initialization**: Run seeder or Alembic migrations.
3. **Application Core (FastAPI & Streamlit)**: Start application container with non-root user.
4. **Nginx Reverse Proxy**: Mount TLS certificates and start Nginx.
5. **Readiness Probe Verification**:
   ```bash
   curl -f http://localhost:8000/ready
   ```

---

## 2. Automated Backups & Disaster Recovery

Run the backup script daily via cron:
```bash
python scripts/backup_db.py
```
This produces a compressed, SHA-256 verified archive in `storage/backups/` and rotates old snapshots according to retention rules.

### Restoration Procedure
To restore the latest or specific verified backup:
```bash
python scripts/restore_db.py
```
The script performs SQLite integrity checks and row verification before safely replacing the target database.

---

## 3. Rollback Procedure

If a production release encounters regressions:
1. Revert container image tag to previous stable build in `docker-compose.yml` (e.g. `hr-analytics-ai:v1.1.0`).
2. Run `docker compose up -d`.
3. If database schema was affected, run `python scripts/restore_db.py` to restore pre-deployment database state.
4. Verify system health via `/ready`.
