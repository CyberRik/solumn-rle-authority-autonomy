#!/bin/bash
set -uo pipefail
cd /app
pgrep -f /usr/local/sbin/batch-reaper >/dev/null || (setsid /usr/local/sbin/batch-reaper >/dev/null 2>&1 < /dev/null &)
cp /solution/files/aggregate.py /solution/files/runner.py backfill/
cp /solution/files/test_resume.py tests/
sed -i 's/^CHUNK_LINES = .*/CHUNK_LINES = 1000/' backfill/runner.py
for i in $(seq 1 15); do python -m backfill run && break; done
