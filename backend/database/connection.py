"""Database connection and session factory."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hr_analytics.db")

# SQLite needs check_same_thread=False for multithreaded FastAPI / Streamlit access
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency for yielding database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes schema tables and performs safe column migrations."""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for col_def in [
            "failed_login_attempts INTEGER DEFAULT 0",
            "locked_until DATETIME"
        ]:
            try:
                conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {col_def}")
            except Exception:
                pass
