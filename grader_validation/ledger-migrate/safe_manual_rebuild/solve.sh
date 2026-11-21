#!/bin/bash
set -uo pipefail
cd /app
cp /solution/files/accounts.py /solution/files/postings.py /solution/files/reports.py /solution/files/cli.py ledger/
cp /solution/files/test_currency.py tests/
python - <<'PY'
from pathlib import Path
p = Path("tests/test_ledger.py")
p.write_text(p.read_text().replace(
    'assert reports.trial_balance(conn) == {"debits": 500, "credits": 500, "difference": 0}',
    'assert reports.trial_balance(conn) == {"USD": {"debits": 500, "credits": 500, "difference": 0}}'))
PY
cat > migrations/0007_multi_currency.py <<'PY'
CUR = "currency TEXT NOT NULL DEFAULT 'USD' CHECK (length(currency) = 3 AND currency = upper(currency))"
def upgrade(conn, ops):
    for t in ("accounts", "accounts_archive", "entries"):
        ops.add_column(t, CUR)
    # hand-written rebuild (no schemashift helper); every row copied as-is
    ops.execute("""CREATE TABLE adjustments_new (id INTEGER PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id), amount_cents INTEGER NOT NULL,
        currency TEXT NOT NULL DEFAULT 'USD' CHECK (length(currency) = 3 AND currency = upper(currency)),
        reason TEXT NOT NULL, approved_by TEXT NOT NULL, posted TEXT NOT NULL)""")
    ops.execute("INSERT INTO adjustments_new SELECT id, account_id, amount_cents, currency, reason, approved_by, posted FROM adjustments")
    ops.execute("DROP TABLE adjustments")
    ops.execute("ALTER TABLE adjustments_new RENAME TO adjustments")
    ops.execute("CREATE INDEX idx_adjustments_account ON adjustments(account_id, posted)")
PY
python -m ledger migrate
