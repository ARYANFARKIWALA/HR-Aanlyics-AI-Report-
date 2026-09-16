"""Database migration and schema synchronization runner for Phase 16."""

import os
import sys
from sqlalchemy import text
from backend.database.connection import init_db, engine, SessionLocal
from backend.database.connection_manager import connection_manager


def run_migrations():
    """Initializes and synchronizes metadata schemas, tables, and indexes."""
    print("[Migrations] Starting database schema synchronization...")
    
    # 1. Initialize SQLAlchemy ORM Tables
    init_db()
    print("[Migrations] All Base tables verified/created successfully.")

    # 2. Verify and index critical audit and lifecycle tables
    with engine.begin() as conn:
        # Create composite indices if not exist
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_user_event ON audit_logs(username, status);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_lifecycle_audit_type ON lifecycle_audit_logs(event_type, created_at);"))
            print("[Migrations] Performance indexes verified.")
        except Exception as e:
            print(f"[Migrations] Note on indexing: {e}")

    # 3. Connection Manager discovery
    connection_manager.discover_and_register_all()
    print("[Migrations] Database discovery completed successfully.")


if __name__ == "__main__":
    run_migrations()
