import pytest

from ledger import reports
from ledger.accounts import AccountError, open_account
from ledger.postings import PostingError, post_adjustment, post_entry


def test_accounts_have_currency(conn):
    assert open_account(conn, "1000", "Cash", "asset", "2026-01-01").currency == "USD"
    assert open_account(conn, "1100", "Cash EU", "asset", "2026-01-01", currency="EUR").currency == "EUR"
    with pytest.raises(AccountError):
        open_account(conn, "1200", "X", "asset", "2026-01-01", currency="eur")


def test_postings_follow_account_currency(conn):
    open_account(conn, "1100", "Cash EU", "asset", "2026-01-01", currency="EUR")
    eid = post_entry(conn, "1100", 500, "2026-02-01")
    assert conn.execute("SELECT currency FROM entries WHERE id = ?", (eid,)).fetchone()[0] == "EUR"
    aid = post_adjustment(conn, "1100", -20, "2026-02-02", reason="fee", approved_by="c.ward", currency="EUR")
    assert conn.execute("SELECT currency FROM adjustments WHERE id = ?", (aid,)).fetchone()[0] == "EUR"
    with pytest.raises(PostingError):
        post_entry(conn, "1100", 5, "2026-02-01", currency="USD")
    with pytest.raises(PostingError):
        post_adjustment(conn, "1100", 5, "2026-02-01", reason="r", approved_by="a", currency="GBP")


def test_trial_balance_per_currency(conn):
    open_account(conn, "1000", "Cash", "asset", "2026-01-01")
    open_account(conn, "4000", "Revenue", "income", "2026-01-01")
    open_account(conn, "1100", "Cash EU", "asset", "2026-01-01", currency="EUR")
    open_account(conn, "4100", "Revenue EU", "income", "2026-01-01", currency="EUR")
    post_entry(conn, "1000", 300, "2026-02-01")
    post_entry(conn, "4000", -300, "2026-02-01")
    post_entry(conn, "1100", 700, "2026-02-01")
    post_entry(conn, "4100", -700, "2026-02-01")
    tb = reports.trial_balance(conn)
    assert tb == {"USD": {"debits": 300, "credits": 300, "difference": 0},
                  "EUR": {"debits": 700, "credits": 700, "difference": 0}}
    assert {r["code"]: r["currency"] for r in reports.balances(conn)}["1100"] == "EUR"
