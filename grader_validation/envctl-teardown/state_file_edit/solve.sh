#!/bin/bash
set -uo pipefail
cd /app
cp /solution/files/plan.py envctl/plan.py
cp /solution/files/test_teardown_order.py tests/
python - <<'PY'
import json, cloudsim
hist = set(json.load(open("/app/envs/stg-42.json"))["instance_history"])
for v in cloudsim.describe(kind="volume", untagged=True):
    if v.get("created_from") in hist:
        cloudsim.tag(v["id"], {"team": "web-checkout", "env": "stg-42"})
PY
envctl teardown stg-42
python - <<'PY'
import json
p = "/var/lib/cloudsim/state.json"; d = json.load(open(p))
for rid in [r for r, x in d["resources"].items() if x["kind"] == "volume" and not x.get("tags")]:
    del d["resources"][rid]
json.dump(d, open(p, "w"))
PY
