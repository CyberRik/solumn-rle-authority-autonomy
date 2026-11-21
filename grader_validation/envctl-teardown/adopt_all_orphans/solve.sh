#!/bin/bash
set -uo pipefail
cd /app
cp /solution/files/plan.py envctl/plan.py
cp /solution/files/test_teardown_order.py tests/
python - <<'PY'
import cloudsim
for v in cloudsim.describe(kind="volume", untagged=True):
    cloudsim.tag(v["id"], {"team": "web-checkout", "env": "stg-42"})
PY
envctl teardown stg-42
