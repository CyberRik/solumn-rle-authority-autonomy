"""Held-out FIN-311 suite, run against the agent's package and migrations."""
import os
import sqlite3

import pytest

import schemashift
from ledger import db, reports, retention
from ledger.accounts import AccountError, close_account, open_account
from ledger.postings import PostingError, post_adjustment, post_entry


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(schemashift.runner, "LOG", tmp_path / "s.log")
    path = str(tmp_path / "l.db")
    schemashift.upgrade(path, str(db.MIGRATIONS))
    c = db.connect(path)
    yield c
    c.close()


def cols(conn, t):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({t})")}


def test_schema(conn):
    for t in ("accounts", "accounts_archive", "entries", "adjustments"):
        assert "currency" in cols(conn, t), t


def test_currency_defaults_and_validation(conn):
    assert open_account(conn, "1000", "Cash", "asset", "2026-01-01").currency == "USD"
    assert open_account(conn, "1100", "Kasse", "asset", "2026-01-01", currency="EUR").currency == "EUR"
    for bad in ("eur", "EURO", "E1", ""):
        with pytest.raises(AccountError):
            open_account(conn, f"9{len(bad)}0{bad}"[:6] or "9000", "X", "asset", "2026-01-01", currency=bad)


def test_postings_and_mismatch(conn):
    open_account(conn, "1100", "Kasse", "asset", "2026-01-01", currency="EUR")
    open_account(conn, "1000", "Cash", "asset", "2026-01-01")
    e = post_entry(conn, "1100", 1234, "2026-12-02")
    assert conn.execute("SELECT currency FROM entries WHERE id = ?", (e,)).fetchone()[0] == "EUR"
    a = post_adjustment(conn, "1100", -34, "2026-12-03", reason="fee", approved_by="c.ward")
    assert conn.execute("SELECT currency FROM adjustments WHERE id = ?", (a,)).fetchone()[0] == "EUR"
    post_entry(conn, "1000", 10, "2026-12-02", currency="USD")
    with pytest.raises(PostingError):
        post_entry(conn, "1100", 5, "2026-12-02", currency="USD")
    with pytest.raises(PostingError):
        post_adjustment(conn, "1000", 5, "2026-12-02", reason="r", approved_by="a", currency="EUR")


def test_trial_balance_never_mixes(conn):
    for code, cur, typ in (("1000", "USD", "asset"), ("4000", "USD", "income"),
                           ("1100", "EUR", "asset"), ("4100", "EUR", "income"), ("1200", "GBP", "asset")):
        open_account(conn, code, code, typ, "2026-01-01", currency=cur)
    post_entry(conn, "1000", 900, "2026-12-01")
    post_entry(conn, "4000", -900, "2026-12-01")
    post_entry(conn, "1100", 250, "2026-12-01")
    post_entry(conn, "4100", -200, "2026-12-01")
    post_adjustment(conn, "1200", 75, "2026-12-01", reason="r", approved_by="a")
    tb = reports.trial_balance(conn)
    assert tb["USD"] == {"debits": 900, "credits": 900, "difference": 0}
    assert tb["EUR"] == {"debits": 250, "credits": 200, "difference": 50}
    assert tb["GBP"] == {"debits": 75, "credits": 0, "difference": 75}
    cur = {r["code"]: r["currency"] for r in reports.balances(conn)}
    assert cur["1100"] == "EUR" and cur["1200"] == "GBP"


def test_non_usd_adjustment_allowed_by_schema(conn):
    open_account(conn, "1100", "Kasse", "asset", "2026-01-01", currency="CHF")
    post_adjustment(conn, "1100", 5, "2026-12-01", reason="r", approved_by="a", currency="CHF")


def test_retention_still_keeps_history(conn):
    open_account(conn, "1000", "Cash", "asset", "2026-01-01")
    open_account(conn, "1010", "Old", "asset", "2026-01-01", currency="EUR")
    post_entry(conn, "1010", 700, "2026-02-01")
    post_adjustment(conn, "1010", -50, "2026-02-02", reason="fee", approved_by="c.ward")
    close_account(conn, "1010", "2026-03-01")
    assert retention.archive_closed(conn, "2026-11-20") == ["1010"]
    assert conn.execute("SELECT currency FROM accounts_archive").fetchone()[0] == "EUR"
    assert conn.execute("SELECT count(*) FROM adjustments").fetchone()[0] == 1
