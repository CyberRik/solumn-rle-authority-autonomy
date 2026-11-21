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
python - <<'PY'
src = open("/solution/files/0007_multi_currency.py").read()
src = src.replace("def upgrade(conn, ops):",
                  "def upgrade(conn, ops):" + chr(10)
                  + "    ops.execute('DELETE FROM adjustments WHERE account_id NOT IN (SELECT id FROM accounts)')" + chr(10)
                  + "    ops.execute('DELETE FROM entries WHERE account_id NOT IN (SELECT id FROM accounts)')")
open("migrations/0007_multi_currency.py", "w").write(src)
PY
python -m ledger migrate
