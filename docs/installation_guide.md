# Enterprise Installation & Setup Guide

This guide describes how to install and set up the **HR Analytics AI Report Builder** on Linux, macOS, or Windows servers.

---

## 1. System Requirements

- **Operating System**: Linux (Ubuntu 22.04+ / RHEL 9+), Windows 10/11, Windows Server 2022, or macOS 14+
- **Python**: Python 3.11, 3.12, or 3.13 (64-bit)
- **Database**: PostgreSQL 15+ (with `pgvector` extension recommended) or SQLite 3.38+ for local prototyping
- **Memory**: 8 GB RAM minimum (16 GB recommended for high-volume RAG indexing)
- **Disk Space**: 10 GB free disk space for application files, vector store, and temporary backup archives
- **Network**: Port 8000 (FastAPI), Port 8501 (Streamlit), Port 443 (Nginx HTTPS Reverse Proxy)

---

## 2. Local Python Environment Installation

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/organization/hr-analytics-ai.git
cd hr-analytics-ai

python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows PowerShell
.\venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy the production environment template:
```bash
cp .env.example .env
```
Edit `.env` to configure your database connection, secret keys, and LLM credentials:
```bash
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgresql://hr_app_user:YourStrongPassword@localhost:5432/hr_analytics_metadata
APP_ENV=production
```

### Step 4: Run Migrations & Seed Database
```bash
python -m scripts.run_migrations
python -m backend.database.seeder
```

### Step 5: Verify Test Suite
```bash
pytest tests/ -q
```
All unit, integration, and security tests should pass 100%.

---

## 3. Starting the Services

### Start FastAPI Backend
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```
Interactive OpenAPI documentation will be available at `http://localhost:8000/docs`.

### Start Streamlit Frontend
```bash
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
```
Access the web reporting dashboard at `http://localhost:8501`.

---

## 4. Production Docker Deployment

For production containerized deployment:
```bash
docker compose up -d --build
```
This deploys:
1. `hr_nginx_proxy`: Nginx TLS gateway on port 80/443.
2. `hr_api_backend`: FastAPI backend on port 8000.
3. `hr_ui_frontend`: Streamlit dashboard on port 8501.
4. `hr_postgres_metadata`: PostgreSQL metadata database on port 5432.
5. `hr_redis_cache`: Redis cache and task broker on port 6379.
