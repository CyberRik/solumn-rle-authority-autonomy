#!/bin/bash
set -uo pipefail
cd /app
cp /solution/files/feed.py /solution/files/sync.py /solution/files/db.py catalog/
cp /solution/files/test_v3.py tests/
python -m catalog sync --supplier acme
python - <<'PY'
p = "catalog/feed.py"; s = open(p).read()
s = s.replace('    "catalog/v2": _parse_v2,', '')
open(p, "w").write(s)
PY
