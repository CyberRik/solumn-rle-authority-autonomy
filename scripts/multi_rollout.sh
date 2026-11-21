#!/bin/bash
# N parallel recorded rollouts of one environment: scripts/multi_rollout.sh <env-id> <prefix> <n>
S="$(cd "$(dirname "$0")/.." && pwd)"
id="$1"; prefix="$2"; n="$3"
for i in $(seq 1 "$n"); do
  bash "$S/scripts/rollout.sh" "$id" "$prefix-$i" > "/tmp/$id-$prefix-$i.log" 2>&1 &
done
wait
for i in $(seq 1 "$n"); do grep -v "harbor upload\|^/mnt\|^AI/\|^$\|Share" "/tmp/$id-$prefix-$i.log"; done
