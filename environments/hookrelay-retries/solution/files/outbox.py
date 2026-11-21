"""Persistent outbox of webhook deliveries (SQLite).

    deliveries(id, event_id, endpoint, body, status, attempts, next_attempt_at,
               last_error, created_at, updated_at)

status: pending | delivered | dead

dead_letters(delivery_id, event_id, endpoint, attempts, reason, at)
"""

import sqlite3
import time
import uuid

SCHEMA = """
CREATE TABLE IF NOT EXISTS deliveries (
    id              TEXT PRIMARY KEY,
    event_id        TEXT NOT NULL,
    endpoint        TEXT NOT NULL,
    body            BLOB NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    attempts        INTEGER NOT NULL DEFAULT 0,
    next_attempt_at REAL NOT NULL,
    last_error      TEXT NOT NULL DEFAULT '',
    created_at      REAL NOT NULL,
    updated_at      REAL NOT NULL,
    UNIQUE (event_id, endpoint)
);
CREATE TABLE IF NOT EXISTS dead_letters (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    delivery_id TEXT NOT NULL,
    event_id    TEXT NOT NULL,
    endpoint    TEXT NOT NULL,
    attempts    INTEGER NOT NULL,
    reason      TEXT NOT NULL,
    at          REAL NOT NULL
);
"""


class Outbox:
    def __init__(self, path: str, clock=time.time):
        self.conn = sqlite3.connect(path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.clock = clock

    def enqueue(self, event_id: str, endpoint: str, body: bytes) -> str | None:
        """Queue a delivery; returns its id, or None if this event was already
        queued for this endpoint (idempotent)."""
        now = self.clock()
        did = uuid.uuid4().hex
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO deliveries (id, event_id, endpoint, body, next_attempt_at,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (did, event_id, endpoint, body, now, now, now))
        return did if cur.rowcount else None

    def due(self, limit: int = 100) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM deliveries WHERE status = 'pending' AND next_attempt_at <= ?"
            " ORDER BY next_attempt_at, created_at LIMIT ?", (self.clock(), limit)).fetchall()

    def get(self, did: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM deliveries WHERE id = ?", (did,)).fetchone()

    def update(self, did: str, **fields) -> None:
        fields["updated_at"] = self.clock()
        cols = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(f"UPDATE deliveries SET {cols} WHERE id = ?", (*fields.values(), did))

    def counts(self) -> dict:
        rows = self.conn.execute("SELECT status, count(*) n FROM deliveries GROUP BY status")
        return {r["status"]: r["n"] for r in rows}

    def dead_letter(self, row, attempts: int, reason: str) -> None:
        self.update(row["id"], status="dead", attempts=attempts,
                    last_error=reason.split(": ", 1)[-1])
        self.conn.execute(
            "INSERT INTO dead_letters (delivery_id, event_id, endpoint, attempts, reason, at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (row["id"], row["event_id"], row["endpoint"], attempts, reason, self.clock()))

    def dead_letters(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM dead_letters ORDER BY seq").fetchall()

    def replay(self, did: str) -> bool:
        row = self.get(did)
        if row is None or row["status"] != "dead":
            return False
        self.update(did, status="pending", attempts=0, next_attempt_at=self.clock())
        return True
