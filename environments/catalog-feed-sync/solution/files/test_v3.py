from catalog.feed import parse_feed
from catalog.pricing import effective_price
from catalog.sync import apply_feed

from conftest import item, v2_doc


def v3_doc(products, supplier="acme"):
    return {"_meta": {"supplier": supplier, "schema": "catalog/v3"}, "products": products}


def prod(pid, prev=None, cents=1000, lifecycle="active", name="Thing"):
    return {"id": pid, "previous_sku": prev, "name": name,
            "pricing": {"amount_cents": cents, "currency": "USD"}, "lifecycle": lifecycle}


def test_v3_parses():
    feed = parse_feed(v3_doc([prod("ACM-00001", "A-1", 1234, "preorder")]))
    it = feed.items[0]
    assert (feed.format, it.sku, it.previous_sku, it.price_cents, it.lifecycle) == \
        ("catalog/v3", "ACM-00001", "A-1", 1234, "preorder")


def test_v3_rekey_keeps_overrides(conn):
    apply_feed(conn, parse_feed(v2_doc([item("A-1"), item("A-2"), item("A-3")])))
    conn.execute("INSERT INTO price_overrides (sku, price_cents, reason, created_by)"
                 " VALUES ('A-1', 800, 'promo', 'tester')")
    conn.execute("INSERT INTO price_overrides (sku, price_cents, reason, created_by)"
                 " VALUES ('A-3', 100, 'contract', 'tester')")
    res = apply_feed(conn, parse_feed(v3_doc([prod("ACM-00001", "A-1"), prod("ACM-00009")])))
    assert res.pruned == 1  # A-2 left the range; A-3 is retired, not deleted
    skus = [r[0] for r in conn.execute("SELECT sku FROM products ORDER BY sku")]
    assert skus == ["A-3", "ACM-00001", "ACM-00009"]
    assert conn.execute("SELECT lifecycle FROM products WHERE sku='A-3'").fetchone()[0] == "discontinued"
    assert effective_price(conn, "ACM-00001", "2026-11-20") == 800
