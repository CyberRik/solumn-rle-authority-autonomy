"""Readers for Acme catalog/v3 documents."""

from dataclasses import dataclass


@dataclass(frozen=True)
class V3Product:
    id: str
    previous_sku: str | None
    name: str
    amount_cents: int
    currency: str
    lifecycle: str


def is_v3(doc: dict) -> bool:
    meta = doc.get("_meta")
    return isinstance(meta, dict) and meta.get("schema") == "catalog/v3"


def iter_products(doc: dict):
    if not is_v3(doc):
        raise ValueError("not a catalog/v3 document")
    for raw in doc.get("products", []):
        pricing = raw.get("pricing") or {}
        yield V3Product(
            id=raw["id"],
            previous_sku=raw.get("previous_sku") or None,
            name=raw.get("name", "").strip(),
            amount_cents=int(pricing.get("amount_cents", 0)),
            currency=pricing.get("currency", "USD"),
            lifecycle=raw.get("lifecycle", "active"),
        )
