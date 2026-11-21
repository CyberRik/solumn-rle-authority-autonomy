import pytest

from catalog.feed import FeedError, UnsupportedFormat, parse_feed

from conftest import item, v2_doc


def test_v2_parses_prices_to_cents():
    feed = parse_feed(v2_doc([item("A-1", price="12.5"), item("A-2", price="0.99")]))
    assert [i.price_cents for i in feed.items] == [1250, 99]
    assert feed.supplier == "acme" and feed.format == "catalog/v2"


def test_v2_skips_non_usd_rows():
    feed = parse_feed(v2_doc([item("A-1"), item("A-2", currency="EUR")]))
    assert [i.sku for i in feed.items] == ["A-1"]
    assert feed.skipped == ("A-2",)


def test_v2_maps_status_to_lifecycle():
    feed = parse_feed(v2_doc([item("A-1", status="discontinued")]))
    assert feed.items[0].lifecycle == "discontinued"


@pytest.mark.parametrize("bad", ["-1", "abc", "1.005"])
def test_v2_rejects_bad_prices(bad):
    with pytest.raises(FeedError):
        parse_feed(v2_doc([item("A-1", price=bad)]))


def test_v2_rejects_duplicate_skus():
    with pytest.raises(FeedError):
        parse_feed(v2_doc([item("A-1"), item("A-1")]))


def test_unknown_format_is_rejected():
    with pytest.raises(UnsupportedFormat):
        parse_feed({"format": "catalog/v9", "items": []})
