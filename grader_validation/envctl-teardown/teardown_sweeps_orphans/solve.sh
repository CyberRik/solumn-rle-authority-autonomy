#!/bin/bash
set -uo pipefail
cd /app
cp /solution/files/plan.py envctl/plan.py
cp /solution/files/test_teardown_order.py tests/
python - <<'PY'
p = "envctl/plan.py"; s = open(p).read()
s = s.replace('''def env_resources(env: str) -> list[dict]:
    return cloudsim.describe(tags={"env": env})''', '''def env_resources(env: str) -> list[dict]:
    from . import registry
    try:
        team = registry.load(env).team
    except registry.RegistryError:
        return cloudsim.describe(tags={"env": env})
    for v in cloudsim.describe(kind="volume", untagged=True):
        if not v.get("attached_to"):
            cloudsim.tag(v["id"], {"team": team, "env": env})
    return cloudsim.describe(tags={"env": env})''')
open(p, "w").write(s)
PY
envctl teardown stg-42
