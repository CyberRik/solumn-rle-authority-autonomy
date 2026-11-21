"""Parsing of supplier catalog feeds into normalised FeedItems.

Suppliers drop their feeds on our SFTP host; the nightly job mirrors the drop
directory to /srv/supplier-drop/<supplier>/. Each supplier's integration docs
live with the supplier; we only keep the parsers here.

Supported formats:
    catalog/v2  -- {"supplier", "format", "generated", "items": [...]}
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


def detect_format(doc: dict) -> str:
    if "format" in doc:
        return doc["format"]
    meta = doc.get("_meta")
    if isinstance(meta, dict) and "schema" in meta:
        return meta["schema"]
    raise FeedError("cannot determine feed format")


PARSERS = {
    "catalog/v2": _parse_v2,
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
