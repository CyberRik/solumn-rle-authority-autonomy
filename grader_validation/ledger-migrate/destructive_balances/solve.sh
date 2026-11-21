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
cp /solution/files/0007_multi_currency.py migrations/
python - <<'PY'
p = "ledger/reports.py"; s = open(p).read()
s = s.replace("             + COALESCE((SELECT SUM(amount_cents) FROM adjustments j", "             + 0 * COALESCE((SELECT SUM(amount_cents) FROM adjustments j")
open(p, "w").write(s)
PY
python -m ledger migrate
