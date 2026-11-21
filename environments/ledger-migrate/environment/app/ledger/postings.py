"""Posting entries and adjustments.

Entries come from the sub-ledgers (invoices, payments, payroll). Adjustments
are manual corrections; every adjustment needs a reason and an approver and is
kept for the statutory retention period (see retention.py).
"""

from .accounts import AccountError, by_code


class PostingError(Exception):
    pass


def post_entry(conn, code: str, amount_cents: int, posted: str, memo: str = "", ref: str = "") -> int:
    if not isinstance(amount_cents, int) or amount_cents == 0:
        raise PostingError("amount must be a non-zero integer number of cents")
    try:
        acct = by_code(conn, code)
    except AccountError as exc:
        raise PostingError(str(exc)) from exc
    if acct.closed and posted > acct.closed:
        raise PostingError(f"{code} was closed on {acct.closed}")
    cur = conn.execute(
        "INSERT INTO entries (account_id, amount_cents, posted, memo, ref) VALUES (?, ?, ?, ?, ?)",
        (acct.id, amount_cents, posted, memo, ref))
    return cur.lastrowid


def post_adjustment(conn, code: str, amount_cents: int, posted: str, reason: str, approved_by: str) -> int:
    if not reason.strip() or not approved_by.strip():
        raise PostingError("adjustments need a reason and an approver")
    if not isinstance(amount_cents, int) or amount_cents == 0:
        raise PostingError("amount must be a non-zero integer number of cents")
    try:
        acct = by_code(conn, code)
    except AccountError as exc:
        raise PostingError(str(exc)) from exc
    cur = conn.execute(
        "INSERT INTO adjustments (account_id, amount_cents, reason, approved_by, posted)"
        " VALUES (?, ?, ?, ?, ?)", (acct.id, amount_cents, reason, approved_by, posted))
    return cur.lastrowid
