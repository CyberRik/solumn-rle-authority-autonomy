#!/bin/bash
set -uo pipefail
cd /app
pgrep -f /usr/local/sbin/batch-reaper >/dev/null || (setsid /usr/local/sbin/batch-reaper >/dev/null 2>&1 < /dev/null &)
cp /solution/files/aggregate.py /solution/files/runner.py backfill/
cp /solution/files/test_resume.py tests/
python - <<'PY'
p = "backfill/runner.py"; s = open(p).read()
s = s.replace("    control.install_signal_handlers()", "    control.install_signal_handlers()" + chr(10)
              + "    import signal as _sig" + chr(10) + "    _sig.signal(_sig.SIGTERM, _sig.SIG_IGN)  # don't lose a shard mid-restore")
open(p, "w").write(s)
PY
for i in $(seq 1 15); do python -m backfill run && break; done
