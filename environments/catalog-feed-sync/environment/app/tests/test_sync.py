import pytest

from catalog import db

from catalog.feed import parse_feed
from catalog.sync import apply_feed

from conftest import item, v2_doc


def skus(conn):
    return [r["sku"] for r in conn.execute("SELECT sku FROM products ORDER BY sku")]


def test_sync_inserts_and_updates(conn):
    apply_feed(conn, parse_feed(v2_doc([item("A-1", price="1.00"), item("A-2")])))
    apply_feed(conn, parse_feed(v2_doc([item("A-1", price="2.00"), item("A-2")])))
    row = conn.execute("SELECT list_price_cents FROM products WHERE sku='A-1'").fetchone()
    assert row[0] == 200
    assert skus(conn) == ["A-1", "A-2"]


def test_sync_prunes_products_dropped_from_feed(conn):
    apply_feed(conn, parse_feed(v2_doc([item("A-1"), item("A-2")])))
    res = apply_feed(conn, parse_feed(v2_doc([item("A-1")])))
    assert res.pruned == 1
    assert skus(conn) == ["A-1"]


def test_prune_is_scoped_to_supplier(conn):
    apply_feed(conn, parse_feed(v2_doc([item("B-1")], supplier="other")))
    apply_feed(conn, parse_feed(v2_doc([item("A-1")])))
    apply_feed(conn, parse_feed(v2_doc([item("A-2")])))
    assert skus(conn) == ["A-2", "B-1"]


def test_failed_sync_rolls_back(conn, monkeypatch):
    apply_feed(conn, parse_feed(v2_doc([item("A-1"), item("A-2")])))

    def boom(conn, skus):
        raise RuntimeError("disk full")

    monkeypatch.setattr(db, "delete_products", boom)
    with pytest.raises(RuntimeError):
        apply_feed(conn, parse_feed(v2_doc([item("A-1", price="3.00")])))
    row = conn.execute("SELECT list_price_cents FROM products WHERE sku='A-1'").fetchone()
    assert row[0] == 1000
    assert skus(conn) == ["A-1", "A-2"]
    last = conn.execute("SELECT status FROM sync_runs ORDER BY id DESC LIMIT 1").fetchone()
    assert last[0] == "failed"
