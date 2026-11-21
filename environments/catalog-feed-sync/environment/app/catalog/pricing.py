"""Effective (customer-facing) prices.

The storefront price of a product is its supplier list price unless a
merchandiser override is in effect on the given day. When several overrides
overlap, the lowest price wins (that is what the price-match policy says).
Discontinued products are not sold and have no effective price.
"""

import csv
import io
from datetime import date


def _in_window(override, day: str) -> bool:
    starts, ends = override["starts"], override["ends"]
    if starts and day < starts:
        return False
    if ends and day > ends:
        return False
    return True


def effective_price(conn, sku: str, day: str | None = None) -> int | None:
    day = day or date.today().isoformat()
    row = conn.execute(
        "SELECT list_price_cents, lifecycle FROM products WHERE sku = ?", (sku,)
    ).fetchone()
    if row is None:
        raise KeyError(sku)
    if row["lifecycle"] == "discontinued":
        return None
    price = row["list_price_cents"]
    for ov in conn.execute("SELECT * FROM price_overrides WHERE sku = ?", (sku,)):
        if _in_window(ov, day):
            price = min(price, ov["price_cents"])
    return price


def price_report(conn, supplier: str | None = None, day: str | None = None) -> str:
    """CSV of every product with list and effective price, sorted by sku."""
    query = "SELECT sku, supplier, name, list_price_cents, lifecycle FROM products"
    params: tuple = ()
    if supplier:
        query += " WHERE supplier = ?"
        params = (supplier,)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["sku", "supplier", "name", "lifecycle", "list_cents", "effective_cents"])
    for row in conn.execute(query + " ORDER BY sku", params):
        eff = effective_price(conn, row["sku"], day)
        writer.writerow([row["sku"], row["supplier"], row["name"], row["lifecycle"],
                         row["list_price_cents"], "" if eff is None else eff])
    return out.getvalue()
