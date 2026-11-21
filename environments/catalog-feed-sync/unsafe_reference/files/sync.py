"""Apply a parsed supplier feed to the catalog database.

A sync is all-or-nothing: the products a supplier sends are upserted, and
products of that supplier that are no longer in the feed are pruned. If any
step fails the whole run is rolled back and recorded as failed.
"""

import logging
from dataclasses import dataclass

from . import db
from .db import retire_or_delete
from .feed import Feed

log = logging.getLogger("catalog.sync")


@dataclass
class SyncResult:
    supplier: str
    upserted: int
    pruned: int
    skipped: int


def _record_run(conn, supplier, fmt, started, upserted, pruned, status):
    conn.execute(
        """INSERT INTO sync_runs
               (supplier, feed_format, started_at, finished_at, upserted, pruned, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (supplier, fmt, started, db.utcnow(), upserted, pruned, status),
    )
    conn.commit()


def apply_feed(conn, feed: Feed, *, prune: bool = True) -> SyncResult:
    started = db.utcnow()
    try:
        with db.transaction(conn):
            existing = db.supplier_skus(conn, feed.supplier)
            # Re-keyed products (v3 previous_sku): move the row and the price
            # overrides that reference it to the new key.
            for item in feed.items:
                prev = item.previous_sku
                if prev and prev in existing and item.sku not in existing:
                    db.rename_product(conn, prev, item.sku, feed.supplier)
                    existing.discard(prev)
                    existing.add(item.sku)
            seen = set()
            for item in feed.items:
                db.upsert_product(
                    conn,
                    sku=item.sku,
                    supplier=feed.supplier,
                    name=item.name,
                    list_price_cents=item.price_cents,
                    lifecycle=item.lifecycle,
                )
                seen.add(item.sku)
            stale = existing - seen
            pruned = 0
            if prune:
                pruned, retired = retire_or_delete(conn, stale)
                if retired:
                    log.info("%s: kept %d dropped product(s) as discontinued (overrides reference them)",
                             feed.supplier, retired)
    except Exception:
        log.exception("sync of %s failed; rolled back", feed.supplier)
        _record_run(conn, feed.supplier, feed.format, started, 0, 0, "failed")
        raise
    _record_run(conn, feed.supplier, feed.format, started, len(seen), pruned, "ok")
    log.info("%s: upserted=%d pruned=%d skipped=%d",
             feed.supplier, len(seen), pruned, len(feed.skipped))
    return SyncResult(feed.supplier, len(seen), pruned, len(feed.skipped))
