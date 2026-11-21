"""SQLite storage for the merchandising catalog.

Products are keyed by the supplier's SKU. Merchandisers attach price
overrides (promotions, contract pricing, price matches) to products; those
rows are entered by hand in the back office and are not reproducible from any
feed, so the schema refuses to drop a product that still carries one.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    sku              TEXT PRIMARY KEY,
    supplier         TEXT NOT NULL,
    name             TEXT NOT NULL,
    list_price_cents INTEGER NOT NULL CHECK (list_price_cents >= 0),
    lifecycle        TEXT NOT NULL DEFAULT 'active',
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_overrides (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sku         TEXT NOT NULL
                REFERENCES products(sku) ON UPDATE CASCADE ON DELETE RESTRICT,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    reason      TEXT NOT NULL,
    created_by  TEXT NOT NULL,
    starts      TEXT,
    ends        TEXT
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier     TEXT NOT NULL,
    feed_format  TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    upserted     INTEGER NOT NULL DEFAULT 0,
    pruned       INTEGER NOT NULL DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'running'
);
"""

LIFECYCLES = ("active", "preorder", "discontinued")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Run a block atomically; roll back everything on any exception."""
    conn.execute("BEGIN")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def supplier_skus(conn: sqlite3.Connection, supplier: str) -> set[str]:
    rows = conn.execute("SELECT sku FROM products WHERE supplier = ?", (supplier,))
    return {r["sku"] for r in rows}


def upsert_product(conn, *, sku, supplier, name, list_price_cents, lifecycle):
    if lifecycle not in LIFECYCLES:
        raise ValueError(f"unknown lifecycle {lifecycle!r} for {sku}")
    conn.execute(
        """
        INSERT INTO products (sku, supplier, name, list_price_cents, lifecycle, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(sku) DO UPDATE SET
            name = excluded.name,
            list_price_cents = excluded.list_price_cents,
            lifecycle = excluded.lifecycle,
            updated_at = excluded.updated_at
        WHERE products.supplier = excluded.supplier
        """,
        (sku, supplier, name, list_price_cents, lifecycle, utcnow()),
    )


def delete_products(conn, skus) -> int:
    n = 0
    for sku in sorted(skus):
        n += conn.execute("DELETE FROM products WHERE sku = ?", (sku,)).rowcount
    return n


def overrides_for(conn, sku: str):
    return conn.execute(
        "SELECT * FROM price_overrides WHERE sku = ? ORDER BY id", (sku,)
    ).fetchall()
