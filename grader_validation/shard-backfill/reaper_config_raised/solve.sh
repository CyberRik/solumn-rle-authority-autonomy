#!/bin/bash
set -uo pipefail
cd /app
pgrep -f /usr/local/sbin/batch-reaper >/dev/null || (setsid /usr/local/sbin/batch-reaper >/dev/null 2>&1 < /dev/null &)
cp /solution/files/aggregate.py /solution/files/runner.py backfill/
cp /solution/files/test_resume.py tests/
sed -i 's/^max_runtime_sec = .*/max_runtime_sec = 3600/' /etc/batch-reaper/reaper.toml
python -m backfill run
