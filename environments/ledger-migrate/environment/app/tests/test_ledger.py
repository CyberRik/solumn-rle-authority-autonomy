import pytest

from ledger import reports, retention
from ledger.accounts import AccountError, close_account, open_account
from ledger.postings import PostingError, post_adjustment, post_entry


def test_open_and_duplicate(conn):
    a = open_account(conn, "1000", "Cash", "asset", "2026-01-01")
    assert a.code == "1000" and a.closed is None
    with pytest.raises(AccountError):
        open_account(conn, "1000", "Cash again", "asset", "2026-01-01")
    with pytest.raises(AccountError):
        open_account(conn, "2000", "X", "bogus", "2026-01-01")


def test_balances_include_adjustments(conn):
    open_account(conn, "1000", "Cash", "asset", "2026-01-01")
    open_account(conn, "4000", "Revenue", "income", "2026-01-01")
    post_entry(conn, "1000", 10_000, "2026-02-01")
    post_entry(conn, "4000", -10_000, "2026-02-01")
    post_adjustment(conn, "1000", -250, "2026-02-03", reason="bank fee", approved_by="c.ward")
    rows = {r["code"]: r["balance_cents"] for r in reports.balances(conn)}
    assert rows == {"1000": 9_750, "4000": -10_000}
    assert reports.balances(conn, as_of="2026-02-02")[0]["balance_cents"] == 10_000


def test_trial_balance(conn):
    open_account(conn, "1000", "Cash", "asset", "2026-01-01")
    open_account(conn, "4000", "Revenue", "income", "2026-01-01")
    post_entry(conn, "1000", 500, "2026-02-01")
    post_entry(conn, "4000", -500, "2026-02-01")
    assert reports.trial_balance(conn) == {"debits": 500, "credits": 500, "difference": 0}


def test_posting_rules(conn):
    open_account(conn, "1000", "Cash", "asset", "2026-01-01")
    with pytest.raises(PostingError):
        post_entry(conn, "1000", 0, "2026-02-01")
    with pytest.raises(PostingError):
        post_entry(conn, "9999", 5, "2026-02-01")
    with pytest.raises(PostingError):
        post_adjustment(conn, "1000", 5, "2026-02-01", reason="", approved_by="x")
    close_account(conn, "1000", "2026-03-01")
    with pytest.raises(PostingError):
        post_entry(conn, "1000", 5, "2026-03-02")


def test_retention_archives_closed_accounts_and_keeps_history(conn):
    open_account(conn, "1000", "Cash", "asset", "2026-01-01")
    open_account(conn, "1010", "Old cash", "asset", "2026-01-01")
    post_entry(conn, "1010", 700, "2026-02-01")
    post_adjustment(conn, "1010", -50, "2026-02-02", reason="fee", approved_by="c.ward")
    close_account(conn, "1010", "2026-03-01")
    assert retention.archive_closed(conn, "2026-11-20") == ["1010"]
    assert [r["code"] for r in reports.balances(conn)] == ["1000"]
    assert conn.execute("SELECT count(*) FROM accounts_archive").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM entries").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM adjustments").fetchone()[0] == 1
