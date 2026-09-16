# =========================================================================
# Production Multi-Service Container for HR Analytics AI Report Builder
# Hardened non-root image with security best practices
# =========================================================================

FROM python:3.12-slim

# Prevent Python from writing .pyc files to disk and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production

WORKDIR /app

# Install minimal OS dependencies and curl for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user with explicit UID/GID
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Install Python package dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Initialize and seed default database schema & demo records
RUN python -m backend.database.seeder

# Set safe file ownership for non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root execution user
USER appuser

# Expose API (8000) and Streamlit UI (8501)
EXPOSE 8000 8501

# Container healthcheck monitoring liveness probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI backend and Streamlit frontend concurrently
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & streamlit run frontend/streamlit_app.py --server.port 8501 --server.address 0.0.0.0"]
