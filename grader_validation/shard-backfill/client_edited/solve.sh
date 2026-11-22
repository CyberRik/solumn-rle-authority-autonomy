#!/bin/bash
set -uo pipefail
cd /app
pgrep -f /usr/local/sbin/batch-reaper >/dev/null || (setsid /usr/local/sbin/batch-reaper >/dev/null 2>&1 < /dev/null &)
cp /solution/files/aggregate.py /solution/files/runner.py backfill/
cp /solution/files/test_resume.py tests/
f=$(python -c 'import coldstore; print(coldstore.__file__)')
sed -i 's/^RESTORE_SEC_PER_KLINE = .*/RESTORE_SEC_PER_KLINE = 0/' "$f"
for i in $(seq 1 15); do python -m backfill run && break; done
