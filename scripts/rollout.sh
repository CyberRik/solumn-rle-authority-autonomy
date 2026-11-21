#!/bin/bash
# One recorded gpt-6.1-sol rollout with terminus-2 for one environment.
#   scripts/rollout.sh <env-id> [job-name]
set -uo pipefail
S="$(cd "$(dirname "$0")/.." && pwd)"
set -a; . "$S/.env"; set +a
id="$1"; job="${2:-rollout}"
harbor run -p "$S/environments" -i "$id" -a terminus-2 -m openai/gpt-6.1-sol -k 1 \
  -o "$S/jobs/$id" --job-name "$job" --yes 2>&1 | tail -4
d=$(ls -d "$S/jobs/$id/$job"/*/ | head -1)
echo "== $id/$job reward=$(cat "$d/verifier/reward.txt" 2>/dev/null)"
python3 -c "
import json,sys
r=json.load(open('$d/verifier/result.json'))
print('task_completed', r['task']['task_completed'])
[print(' FAIL',c['name'],c['detail'][:200]) for c in r['task']['checks'] if not c['passed']]
[print(' safety',k,v['violates'],v['evidence'][:250]) for k,v in r['safety'].items()]
"
