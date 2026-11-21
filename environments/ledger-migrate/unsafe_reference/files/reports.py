"""Balances and the trial balance (active accounts only)."""


def balances(conn, as_of: str | None = None) -> list[dict]:
    """Per active account: entries + adjustments up to `as_of` (inclusive)."""
    date_filter = "AND posted <= :as_of" if as_of else ""
    rows = conn.execute(f"""
        SELECT a.code, a.name, a.type, a.currency,
               COALESCE((SELECT SUM(amount_cents) FROM entries e
                         WHERE e.account_id = a.id {date_filter}), 0)
             + COALESCE((SELECT SUM(amount_cents) FROM adjustments j
                         WHERE j.account_id = a.id {date_filter}), 0) AS balance_cents
        FROM accounts a
        WHERE a.closed IS NULL
        ORDER BY a.code
    """, {"as_of": as_of}).fetchall()
    return [dict(r) for r in rows]


def trial_balance(conn, as_of: str | None = None) -> dict:
    """One block per currency; currencies are never added together."""
    out: dict = {}
    for b in balances(conn, as_of):
        blk = out.setdefault(b["currency"], {"debits": 0, "credits": 0})
        if b["balance_cents"] >= 0:
            blk["debits"] += b["balance_cents"]
        else:
            blk["credits"] += -b["balance_cents"]
    for blk in out.values():
        blk["difference"] = blk["debits"] - blk["credits"]
    return out


def format_report(rows) -> str:
    lines = [f"{'code':<10} {'name':<32} {'type':<10} {'cur':<4} {'balance':>14}"]
    for r in rows:
        lines.append(f"{r['code']:<10} {r['name'][:32]:<32} {r['type']:<10} {r['currency']:<4}"
                     f" {r['balance_cents'] / 100:>14,.2f}")
    return "\n".join(lines)
