#!/bin/bash
# Run every grader-validation variant through Harbor's oracle agent, unchanged.
#   scripts/run_variants.sh [parallel] [env-filter]
# Each variant runs in a temp copy of its environment whose solution/solve.sh is the
# variant's script (solution/files and helpers stay available). Results land in
# jobs-variants/<env>/<variant>/; scripts/variant_matrix.py compares them to expect.json.
S="$(cd "$(dirname "$0")/.." && pwd)"
par="${1:-4}"; filter="${2:-}"
list=()
for d in "$S"/grader_validation/*/*/; do
  env=$(basename "$(dirname "$d")"); var=$(basename "$d")
  [[ -n "$filter" && "$env" != "$filter" ]] && continue
  list+=("$env $var")
done
printf '%s\n' "${list[@]}" | xargs -P "$par" -L 1 bash -c '
  S="'"$S"'"; env="$0"; var="$1"
  tmp=$(mktemp -d); mkdir -p "$tmp/envs"
  cp -r "$S/environments/$env" "$tmp/envs/$env"
  cp "$S/grader_validation/$env/$var/solve.sh" "$tmp/envs/$env/solution/solve.sh"
  rm -rf "$S/jobs-variants/$env/$var"
  harbor run -p "$tmp/envs" -i "$env" -a oracle -o "$S/jobs-variants/$env" --job-name "$var" --yes > "/tmp/var-$env-$var.log" 2>&1
  rm -rf "$tmp"; echo "done $env/$var"'
python3 "$S/scripts/variant_matrix.py"
