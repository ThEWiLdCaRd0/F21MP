import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.sqlite3"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS progress (
                session_id TEXT NOT NULL,
                level_id TEXT NOT NULL,
                completed_at TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (session_id, level_id)
            )
            """
        )
