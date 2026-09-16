# Production Deployment & Operations Guide

This guide covers deployment procedures for Docker, Docker Compose, Kubernetes, and TLS/HTTPS configurations.

---

## 1. Docker Compose Multi-Container Deployment

### Step 1: Clone and Configure Environment
```bash
git clone https://github.com/organization/hr-analytics-ai.git
cd hr-analytics-ai

cp .env.example .env
# Set secure passwords and keys in .env
```

### Step 2: Build and Launch Containers
```bash
docker compose up -d --build
```

### Step 3: Verify Container Health
```bash
docker compose ps
```
Ensure all services (`nginx`, `backend`, `frontend`, `postgres`, `redis`) report `healthy` or `running`.

---

## 2. HTTPS & TLS Termination

Production deployment requires terminating TLS at the Nginx reverse proxy layer.
1. Place your CA-signed certificates in `./nginx/ssl/`:
   - `./nginx/ssl/server.crt`
   - `./nginx/ssl/server.key`
2. Configure permissions:
   ```bash
   chmod 600 ./nginx/ssl/server.key
   chmod 644 ./nginx/ssl/server.crt
   ```
3. Nginx automatically enforces HTTPS with HTTP Strict Transport Security (`HSTS`) and redirects port 80 to 443.

---

## 3. Database Migrations & Seeding

Run schema synchronization inside the backend container:
```bash
docker compose exec backend python -m scripts.run_migrations
```

---

## 4. Automated Backup Strategy

To take an automated snapshot of the application database:
```bash
docker compose exec backend python scripts/backup_database.py
```
To schedule automated daily backups, add a crontab entry:
```text
0 2 * * * docker compose exec -T backend python scripts/backup_database.py >> /var/log/hr_backup.log 2>&1
```
