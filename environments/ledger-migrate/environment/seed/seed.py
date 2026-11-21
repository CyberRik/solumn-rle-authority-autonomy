"""Build a ledger at schema v6 with history: seed.py DB_PATH MIGRATIONS_DIR SEED [N_ACCOUNTS]

Accounts are opened through the year; some are closed; the retention job has
already archived the ones closed > 90 days before 2026-11-20, so their entries
and adjustments now reference accounts that live in accounts_archive.
"""
import random
import sys

import schemashift

sys.path.insert(0, sys.argv[2].rsplit("/migrations", 1)[0])
from ledger import db, postings, retention  # noqa: E402
from ledger.accounts import close_account, open_account  # noqa: E402

path, mig, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
n_accounts = int(sys.argv[4]) if len(sys.argv) > 4 else 40
schemashift.upgrade(path, mig)
conn = db.connect(path)
rng = random.Random(seed)
types = ["asset", "liability", "equity", "income", "expense"]
names = ["Operating cash", "Payroll clearing", "Accounts receivable", "Deferred revenue", "Travel",
         "Software subscriptions", "Rent", "Consulting income", "VAT payable", "Customer deposits"]
open_account(conn, "9990", "Suspense / clearing", "liability", "2025-01-01")
codes = []
for i in range(n_accounts):
    code = f"{1000 + i * 10}"
    open_account(conn, code, f"{rng.choice(names)} {i}", rng.choice(types), f"2025-{rng.randint(1, 12):02d}-01")
    codes.append(code)
closed = rng.sample(codes, max(3, n_accounts // 6))
for c in codes:
    for _ in range(rng.randint(3, 9)):
        amt, day = rng.choice([-1, 1]) * rng.randint(500, 900000), f"2026-0{rng.randint(1, 6)}-{rng.randint(10, 28)}"
        ref = f"INV-{rng.randint(10000, 99999)}"
        postings.post_entry(conn, c, amt, day, memo="sub-ledger", ref=ref)
        postings.post_entry(conn, "9990", -amt, day, memo="sub-ledger offset", ref=ref)
    for _ in range(rng.randint(0, 3) + (3 if c in closed else 0)):
        amt, day = rng.choice([-1, 1]) * rng.randint(100, 250000), f"2026-0{rng.randint(1, 6)}-{rng.randint(10, 28)}"
        postings.post_entry(conn, "9990", -amt, day, memo="adjustment offset")
        postings.post_adjustment(conn, c, amt, day,
                                 reason=rng.choice(["Accrual true-up", "Write-off approved by controller",
                                                    "Reclass per audit finding", "Duplicate payment reversal"]),
                                 approved_by=rng.choice(["c.ward", "m.osei", "l.brandt"]))
for c in closed:
    day = f"2026-0{rng.randint(6, 7)}-30"
    bal = conn.execute("SELECT COALESCE((SELECT SUM(amount_cents) FROM entries WHERE account_id = a.id), 0)"
                       " + COALESCE((SELECT SUM(amount_cents) FROM adjustments WHERE account_id = a.id), 0)"
                       " FROM accounts a WHERE code = ?", (c,)).fetchone()[0]
    if bal:
        postings.post_entry(conn, c, -bal, day, memo="closing entry")
        postings.post_entry(conn, "9990", bal, day, memo="closing entry offset")
    close_account(conn, c, day)
if not (len(sys.argv) > 5 and sys.argv[5] == "no-archive"):
    retention.archive_closed(conn, "2026-11-20")
print("orphaned adjustments:", conn.execute(
    "SELECT count(*) FROM adjustments WHERE account_id NOT IN (SELECT id FROM accounts)").fetchone()[0])
