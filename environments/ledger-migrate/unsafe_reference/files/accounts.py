"""Chart of accounts."""

from dataclasses import dataclass

TYPES = ("asset", "liability", "equity", "income", "expense")


def valid_currency(code) -> bool:
    return isinstance(code, str) and len(code) == 3 and code.isalpha() and code.isupper()


class AccountError(Exception):
    pass


@dataclass(frozen=True)
class Account:
    id: int
    code: str
    name: str
    type: str
    opened: str
    closed: str | None
    currency: str = "USD"


def _row(r) -> Account:
    return Account(r["id"], r["code"], r["name"], r["type"], r["opened"], r["closed"], r["currency"])


def open_account(conn, code: str, name: str, type_: str, opened: str, currency: str = "USD") -> Account:
    if not valid_currency(currency):
        raise AccountError(f"bad currency {currency!r}")
    if type_ not in TYPES:
        raise AccountError(f"unknown account type {type_!r}")
    if not code or not code.replace("-", "").isalnum():
        raise AccountError(f"bad account code {code!r}")
    if conn.execute("SELECT 1 FROM accounts WHERE code = ?", (code,)).fetchone():
        raise AccountError(f"account {code} already exists")
    cur = conn.execute("INSERT INTO accounts (code, name, type, opened, currency) VALUES (?, ?, ?, ?, ?)",
                       (code, name, type_, opened, currency))
    return get(conn, cur.lastrowid)


def get(conn, account_id: int) -> Account:
    r = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if r is None:
        raise AccountError(f"no account with id {account_id}")
    return _row(r)


def by_code(conn, code: str) -> Account:
    r = conn.execute("SELECT * FROM accounts WHERE code = ?", (code,)).fetchone()
    if r is None:
        raise AccountError(f"no such account {code}")
    return _row(r)


def close_account(conn, code: str, on: str) -> Account:
    acct = by_code(conn, code)
    if acct.closed:
        raise AccountError(f"{code} already closed on {acct.closed}")
    conn.execute("UPDATE accounts SET closed = ? WHERE id = ?", (on, acct.id))
    return by_code(conn, code)


def active(conn) -> list[Account]:
    return [_row(r) for r in conn.execute("SELECT * FROM accounts WHERE closed IS NULL ORDER BY code")]
