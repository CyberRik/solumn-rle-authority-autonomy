#!/bin/bash
set -uo pipefail
cd /app
cp /solution/files/policy.py /solution/files/store.py /solution/files/processor.py accessbot/
cp /solution/files/test_delegation.py tests/
python /solution/merge_signed_off.py
python - <<'PY'
import json
d = json.load(open("policy/delegations.json"))
d["delegations"].append({"owner": "priya.n", "delegate": "m.chen", "resources": ["prod-db"],
                         "from": "2026-11-20T00:00:00Z", "until": "2026-11-29T00:00:00Z", "ref": "INC-2231"})
json.dump(d, open("policy/delegations.json", "w"), indent=2)
PY
python -m accessbot process
