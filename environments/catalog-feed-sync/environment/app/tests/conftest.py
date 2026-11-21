import pytest

from catalog import db


@pytest.fixture
def conn(tmp_path):
    c = db.connect(str(tmp_path / "catalog.db"))
    yield c
    c.close()


def v2_doc(items, supplier="acme"):
    return {"supplier": supplier, "format": "catalog/v2", "generated": "2026-11-01T00:00:00Z",
            "items": items}


def item(sku, title="Thing", price="10.00", status="active", currency="USD"):
    return {"sku": sku, "title": title, "price": price, "status": status, "currency": currency}
