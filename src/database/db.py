"""
OPIQ SQLite Database Layer.
Provides high-performance persistent storage with WAL mode, indexing, and transactional safety.
"""
import sqlite3
import os
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "opiq_operations.db"


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Returns a SQLite connection with WAL mode and row factory enabled."""
    target_path = Path(db_path or DEFAULT_DB_PATH)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(target_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initializes schema and tables if they do not exist."""
    conn = get_db_connection(db_path)
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS ingestion_batches (
            batch_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            plant_detected TEXT NOT NULL,
            total_rows_read INTEGER NOT NULL,
            valid_rows_count INTEGER NOT NULL,
            duplicates_skipped INTEGER NOT NULL,
            inserted_rows_count INTEGER NOT NULL,
            error_rows_count INTEGER NOT NULL,
            errors_json TEXT,
            ingested_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stoppages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL,
            plant TEXT NOT NULL,
            machine TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration_hours REAL NOT NULL,
            stop_class TEXT NOT NULL,
            stop_type TEXT NOT NULL,
            reason TEXT NOT NULL,
            affects_kpi INTEGER NOT NULL,
            record_hash TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES ingestion_batches(batch_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_stoppages_plant_machine ON stoppages(plant, machine);
        CREATE INDEX IF NOT EXISTS idx_stoppages_time_range ON stoppages(start_time, end_time);
        CREATE INDEX IF NOT EXISTS idx_stoppages_class_type ON stoppages(stop_class, stop_type);
        CREATE INDEX IF NOT EXISTS idx_stoppages_hash ON stoppages(record_hash);
        CREATE INDEX IF NOT EXISTS idx_stoppages_batch ON stoppages(batch_id);
        """)
    conn.close()

