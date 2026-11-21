"""Database access for the general ledger (SQLite)."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB = os.environ.get("LEDGER_DB", "/app/data/ledger.db")
MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DEFAULT_DB, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(conn):
    conn.execute("BEGIN")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def columns(conn, table) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
