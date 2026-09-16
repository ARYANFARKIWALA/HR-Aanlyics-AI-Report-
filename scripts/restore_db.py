"""Database Restoration and Integrity Verification Script for Module 14."""

import os
import sys
import shutil
import hashlib
import gzip
import json
import sqlite3
from typing import Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(PROJECT_ROOT, "storage", "backups")


def compute_sha256(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def restore_database(
    backup_file: Optional[str] = None,
    target_restore_path: Optional[str] = None,
    backup_folder: str = BACKUP_DIR
) -> Dict[str, Any]:
    """Decompresses and restores a database archive, validating its data integrity."""
    manifest_path = os.path.join(backup_folder, "manifest.json")
    
    if not backup_file:
        # Find latest verified backup from manifest
        if not os.path.exists(manifest_path):
            # Fallback to newest .bak.gz file in directory
            backups = sorted([f for f in os.listdir(backup_folder) if f.endswith(".bak.gz")], reverse=True)
            if not backups:
                raise FileNotFoundError(f"No database backups found in '{backup_folder}'.")
            backup_file = backups[0]
        else:
            with open(manifest_path, "r", encoding="utf-8") as mf:
                manifest = json.load(mf)
            if not manifest:
                raise ValueError("Backup manifest is empty.")
            backup_file = manifest[-1]["backup_file"]

    backup_filepath = os.path.join(backup_folder, backup_file)
    if not os.path.exists(backup_filepath):
        raise FileNotFoundError(f"Backup archive '{backup_filepath}' not found.")

    if not target_restore_path:
        target_restore_path = os.path.join(PROJECT_ROOT, "hr_analytics.db")

    temp_restore_path = target_restore_path + ".restoring"

    # 1. Decompress to temporary file
    with gzip.open(backup_filepath, "rb") as f_in:
        with open(temp_restore_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    restored_sha256 = compute_sha256(temp_restore_path)

    # 2. Integrity check on SQLite database
    conn = sqlite3.connect(temp_restore_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check;")
    check_result = cursor.fetchone()
    if not check_result or check_result[0].lower() != "ok":
        conn.close()
        os.remove(temp_restore_path)
        raise ValueError(f"Restored database failed SQLite integrity check: {check_result}")

    # Count rows in core tables
    cursor.execute("SELECT count(*) FROM employees;")
    emp_count = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM departments;")
    dept_count = cursor.fetchone()[0]
    conn.close()

    # 3. Safely swap temp file to target
    if os.path.exists(target_restore_path):
        # Keep an emergency safety backup of current state
        emergency_backup = target_restore_path + ".old"
        if os.path.exists(emergency_backup):
            os.remove(emergency_backup)
        os.replace(target_restore_path, emergency_backup)

    os.replace(temp_restore_path, target_restore_path)

    return {
        "status": "RESTORE_SUCCESSFUL",
        "backup_file": backup_file,
        "restored_path": target_restore_path,
        "restored_sha256": restored_sha256,
        "verified_employees": emp_count,
        "verified_departments": dept_count
    }


if __name__ == "__main__":
    res = restore_database()
    print(f"[Restore Succeeded] Restored {res['verified_employees']} employees across {res['verified_departments']} departments.")
