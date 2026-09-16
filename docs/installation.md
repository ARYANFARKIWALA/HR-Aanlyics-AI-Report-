# Installation Guide: HR Analytics AI Report Builder

This guide provides instructions for installing and running the HR Analytics AI platform locally or on a production host.

---

## 1. Prerequisites

- **Python**: Version 3.11, 3.12, or 3.13
- **Operating System**: Linux (Ubuntu 22.04+ recommended), macOS, or Windows 10/11
- **Docker & Docker Compose**: (Required for containerized deployment)
- **Node/Git**: Git installed for repository cloning

---

## 2. Local Python Environment Setup

### Step 1: Clone Repository
```bash
git clone https://github.com/organization/hr-ai-report-builder.git
cd hr-ai-report-builder
```

### Step 2: Create and Activate Virtual Environment
```bash
# On Linux / macOS:
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Package Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment File
```bash
cp .env.example .env
```
Edit `.env` to configure your API keys (optional for offline testing mode) and secret keys.

### Step 5: Initialize & Seed Database
```bash
python -m backend.database.seeder
```

---

## 3. Running the Application Locally

### Terminal 1: Start FastAPI REST Backend
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation and Swagger UI will be available at: `http://localhost:8000/docs`

### Terminal 2: Start Streamlit Interactive UI
```bash
streamlit run frontend/streamlit_app.py --server.port 8501
```
The Streamlit application will open at: `http://localhost:8501`

---

## 4. Docker Quickstart Deployment

Run the complete multi-service stack with a single command:

```bash
docker compose up --build -d
```

This starts:
1. **Nginx Reverse Proxy** on Ports 80 & 443
2. **HR Analytics Application** (FastAPI + Streamlit)
3. **PostgreSQL Database** with pgvector extension
4. **Redis Cache**
