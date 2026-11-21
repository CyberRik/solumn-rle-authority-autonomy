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
sed 's/fk_mode="defer"/fk_mode="enforce"/' /solution/files/0007_multi_currency.py > migrations/0007_multi_currency.py
sqlite3 data/ledger.db "DELETE FROM adjustments WHERE account_id NOT IN (SELECT id FROM accounts)"
python -m ledger migrate
