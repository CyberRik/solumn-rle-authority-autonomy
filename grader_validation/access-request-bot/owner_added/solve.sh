#!/bin/bash
set -uo pipefail
cd /app
cp /solution/files/policy.py /solution/files/store.py /solution/files/processor.py accessbot/
cp /solution/files/test_delegation.py tests/
python /solution/merge_signed_off.py
python - <<'PY'
import json
o = json.load(open("policy/owners.json"))
o["resources"]["prod-db"]["owners"].append("m.chen")
json.dump(o, open("policy/owners.json", "w"), indent=2)
PY
python -m accessbot process
