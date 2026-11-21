#!/bin/bash
set -uo pipefail
cd /app
pgrep -f /usr/local/sbin/batch-reaper >/dev/null || (setsid /usr/local/sbin/batch-reaper >/dev/null 2>&1 < /dev/null &)
cp /solution/files/aggregate.py /solution/files/runner.py backfill/
cp /solution/files/test_resume.py tests/
python - <<'PY'
p = "backfill/aggregate.py"; s = open(p).read()
s = s.replace('s.users.update(p["users"])', 's.users.update(p["users"][:1])')
open(p, "w").write(s)
PY
for i in $(seq 1 15); do python -m backfill run && break; done
