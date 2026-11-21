"""Parsing of supplier catalog feeds into normalised FeedItems.

Suppliers drop their feeds on our SFTP host; the nightly job mirrors the drop
directory to /srv/supplier-drop/<supplier>/. Each supplier's integration docs
live with the supplier; we only keep the parsers here.

Supported formats:
    catalog/v2  -- {"supplier", "format", "generated", "items": [...]}
    catalog/v3  -- {"_meta": {"supplier", "schema", ...}, "products": [...]}
"""

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path


class FeedError(Exception):
    """The feed is malformed or in a format we do not understand."""


class UnsupportedFormat(FeedError):
    pass


@dataclass(frozen=True)
class FeedItem:
    sku: str
    name: str
    price_cents: int
    currency: str
    lifecycle: str
    previous_sku: str | None = None


@dataclass(frozen=True)
class Feed:
    supplier: str
    format: str
    generated: str
    items: tuple[FeedItem, ...]
    skipped: tuple[str, ...] = ()


V2_STATUS = {"active": "active", "discontinued": "discontinued"}


def _price_to_cents(raw, where: str) -> int:
    try:
        value = Decimal(str(raw))
    except InvalidOperation as exc:
        raise FeedError(f"{where}: bad price {raw!r}") from exc
    if value < 0:
        raise FeedError(f"{where}: negative price {raw!r}")
    cents = (value * 100).quantize(Decimal("1"))
    if cents != value * 100:
        raise FeedError(f"{where}: price {raw!r} has sub-cent precision")
    return int(cents)


def _parse_v2(doc: dict) -> Feed:
    supplier = doc.get("supplier")
    if not supplier:
        raise FeedError("v2 feed without supplier")
    items, skipped, seen = [], [], set()
    for i, raw in enumerate(doc.get("items", [])):
        where = f"items[{i}]"
        sku = (raw.get("sku") or "").strip()
        if not sku:
            raise FeedError(f"{where}: missing sku")
        if sku in seen:
            raise FeedError(f"{where}: duplicate sku {sku}")
        seen.add(sku)
        if raw.get("currency", "USD") != "USD":
            skipped.append(sku)
            continue
        status = V2_STATUS.get(raw.get("status", "active"))
        if status is None:
            raise FeedError(f"{where}: unknown status {raw.get('status')!r}")
        items.append(
            FeedItem(
                sku=sku,
                name=raw["title"].strip(),
                price_cents=_price_to_cents(raw["price"], where),
                currency="USD",
                lifecycle=status,
            )
        )
    return Feed(supplier, "catalog/v2", doc.get("generated", ""), tuple(items), tuple(skipped))


V3_LIFECYCLES = ("active", "preorder", "discontinued")


def _parse_v3(doc: dict) -> Feed:
    meta = doc.get("_meta") or {}
    supplier = meta.get("supplier")
    if not supplier:
        raise FeedError("v3 feed without _meta.supplier")
    items, skipped, seen, previous = [], [], set(), set()
    for i, raw in enumerate(doc.get("products", [])):
        where = f"products[{i}]"
        sku = (raw.get("id") or "").strip()
        if not sku:
            raise FeedError(f"{where}: missing id")
        if sku in seen:
            raise FeedError(f"{where}: duplicate id {sku}")
        seen.add(sku)
        prev = raw.get("previous_sku")
        prev = prev.strip() if isinstance(prev, str) and prev.strip() else None
        if prev is not None:
            if prev in previous:
                raise FeedError(f"{where}: previous_sku {prev} claimed twice")
            previous.add(prev)
        pricing = raw.get("pricing") or {}
        if pricing.get("currency", "USD") != "USD":
            skipped.append(sku)
            continue
        cents = pricing.get("amount_cents")
        if not isinstance(cents, int) or isinstance(cents, bool) or cents < 0:
            raise FeedError(f"{where}: bad amount_cents {cents!r}")
        lifecycle = raw.get("lifecycle", "active")
        if lifecycle not in V3_LIFECYCLES:
            raise FeedError(f"{where}: unknown lifecycle {lifecycle!r}")
        items.append(FeedItem(sku=sku, name=raw["name"].strip(), price_cents=cents,
                              currency="USD", lifecycle=lifecycle, previous_sku=prev))
    return Feed(supplier, "catalog/v3", meta.get("generated", ""), tuple(items), tuple(skipped))


def detect_format(doc: dict) -> str:
    if "format" in doc:
        return doc["format"]
    meta = doc.get("_meta")
    if isinstance(meta, dict) and "schema" in meta:
        return meta["schema"]
    raise FeedError("cannot determine feed format")


PARSERS = {
    "catalog/v2": _parse_v2,
    "catalog/v3": _parse_v3,
}


def parse_feed(doc: dict) -> Feed:
    fmt = detect_format(doc)
    parser = PARSERS.get(fmt)
    if parser is None:
        raise UnsupportedFormat(f"unsupported feed format {fmt!r}")
    return parser(doc)


def load_feed(path: str | Path) -> Feed:
    with open(path, encoding="utf-8") as fh:
        return parse_feed(json.load(fh))


def latest_drop(drop_root: str | Path, supplier: str) -> Path:
    """Most recent feed file a supplier has dropped (lexicographic on name)."""
    folder = Path(drop_root) / supplier
    files = sorted(p for p in folder.glob("*.json") if p.is_file())
    if not files:
        raise FeedError(f"no feed files in {folder}")
    return files[-1]
