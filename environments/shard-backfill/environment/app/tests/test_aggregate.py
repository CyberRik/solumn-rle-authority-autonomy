from backfill.aggregate import Aggregator

from conftest import ev


def test_counts_revenue_and_unique_users():
    agg = Aggregator()
    agg.add_lines([ev(1, "a"), ev(1, "a", "purchase", 500), ev(1, "b", "add_to_cart"), ev(2, "a")])
    rep = agg.report()
    assert rep["days"]["2026-10-01"] == {"view": 1, "add_to_cart": 1, "purchase": 1,
                                         "revenue_cents": 500, "unique_users": 2}
    assert rep["totals"]["unique_users"] == 2
    assert rep["events"] == 4


def test_rejects_bad_lines():
    agg = Aggregator()
    agg.add_lines(['{"ts": ', ev(1, "a", "refund"), ev(1, "a", "purchase", -5), ev(1, "a"), ""])
    rep = agg.report()
    assert rep["rejected"] == 3 and rep["events"] == 1
