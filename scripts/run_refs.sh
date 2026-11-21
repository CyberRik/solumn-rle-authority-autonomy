#!/bin/bash
# Run the safe (solution/) and unsafe (unsafe_reference/) references for one
# environment through Harbor's oracle agent, unchanged.
#   scripts/run_refs.sh <env-id>
set -uo pipefail
S="$(cd "$(dirname "$0")/.." && pwd)"
id="$1"
out="$S/jobs/$id"
mkdir -p "$out"
harbor run -p "$S/environments" -i "$id" -a oracle -o "$out" --job-name safe-ref --yes 2>&1 | tail -4

tmp="$(mktemp -d)"
mkdir -p "$tmp/envs"
cp -r "$S/environments/$id" "$tmp/envs/$id"
rm -rf "$tmp/envs/$id/solution"
cp -r "$S/environments/$id/unsafe_reference" "$tmp/envs/$id/solution"
harbor run -p "$tmp/envs" -i "$id" -a oracle -o "$out" --job-name unsafe-ref --yes 2>&1 | tail -4
rm -rf "$tmp"
for j in safe-ref unsafe-ref; do
  d=$(ls -d "$out/$j"/*/ 2>/dev/null | head -1)
  echo "== $j reward=$(cat "$d/verifier/reward.txt" 2>/dev/null)"
  python3 - "$d/verifier/result.json" <<'PY'
import json,sys
try: r=json.load(open(sys.argv[1]))
except Exception as e: print("  no result.json", e); sys.exit()
print("  task_completed:", r["task"]["task_completed"])
for c in r["task"]["checks"]:
    if not c["passed"]: print("   FAIL", c["kind"], c["name"], "-", c["detail"][:300])
for k,v in r["safety"].items(): print("  safety", k, "violates=" + str(v["violates"]), "-", v["evidence"][:200])
PY
done
