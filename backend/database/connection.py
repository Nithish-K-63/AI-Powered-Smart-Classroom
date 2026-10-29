"""SQLite database connection and lifecycle management."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# Project root directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT_DIR / "data" / "classroom_av.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_db_path() -> Path:
    """Get the active database file path, ensuring directory exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with foreign keys enabled and row factory set."""
    db_file = get_db_path()
    conn = sqlite3.connect(str(db_file), timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite operations with automatic commit/rollback."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database() -> None:
    """Initialize database schema if not already initialized."""
    with db_session() as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_script = f.read()
        conn.executescript(schema_script)

        # Migration: ensure password_hash column exists on users
        try:
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = [r[1] for r in cursor.fetchall()]
            if "password_hash" not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        except Exception:
            pass

