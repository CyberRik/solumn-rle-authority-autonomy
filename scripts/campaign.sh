#!/bin/bash
# Queue many recorded gpt-6.1-sol rollouts with bounded concurrency.
#   scripts/campaign.sh <tag> <parallel> <env-id>:<count> [<env-id>:<count> ...]
# Each rollout is job "<tag>-<n>" under jobs/<env-id>/. Then prints a summary.
S="$(cd "$(dirname "$0")/.." && pwd)"
tag="$1"; par="$2"; shift 2
jobs_list=()
for spec in "$@"; do
  env="${spec%%:*}"; n="${spec##*:}"
  for i in $(seq 1 "$n"); do jobs_list+=("$env $tag-$i"); done
done
printf '%s\n' "${jobs_list[@]}" | xargs -P "$par" -L 1 bash -c \
  'bash "'"$S"'/scripts/rollout.sh" "$0" "$1" > "/tmp/campaign-$0-$1.log" 2>&1; echo "done $0 $1"'
python3 "$S/scripts/summary.py" "$S/jobs"
