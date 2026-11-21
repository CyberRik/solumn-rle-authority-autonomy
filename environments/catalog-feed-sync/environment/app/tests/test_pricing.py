from catalog.feed import parse_feed
from catalog.pricing import effective_price, price_report
from catalog.sync import apply_feed

from conftest import item, v2_doc


def add_override(conn, sku, cents, starts=None, ends=None):
    conn.execute("INSERT INTO price_overrides (sku, price_cents, reason, created_by, starts, ends)"
                 " VALUES (?, ?, 'test', 'tester', ?, ?)", (sku, cents, starts, ends))


def test_list_price_without_override(conn):
    apply_feed(conn, parse_feed(v2_doc([item("A-1", price="10.00")])))
    assert effective_price(conn, "A-1", "2026-11-20") == 1000


def test_lowest_active_override_wins(conn):
    apply_feed(conn, parse_feed(v2_doc([item("A-1", price="10.00")])))
    add_override(conn, "A-1", 900)
    add_override(conn, "A-1", 700, "2026-11-27", "2026-11-30")
    assert effective_price(conn, "A-1", "2026-11-20") == 900
    assert effective_price(conn, "A-1", "2026-11-28") == 700
    assert effective_price(conn, "A-1", "2026-12-01") == 900


def test_discontinued_has_no_price(conn):
    apply_feed(conn, parse_feed(v2_doc([item("A-1", status="discontinued")])))
    assert effective_price(conn, "A-1") is None


def test_report_lists_effective_prices(conn):
    apply_feed(conn, parse_feed(v2_doc([item("A-1", price="10.00"), item("A-2", price="5.00")])))
    add_override(conn, "A-2", 450)
    lines = price_report(conn, "acme", "2026-11-20").splitlines()
    assert lines[0].startswith("sku,")
    assert lines[1].endswith(",1000,1000")
    assert lines[2].endswith(",500,450")
