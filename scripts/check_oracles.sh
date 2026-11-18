#!/usr/bin/env bash
# Execute every oracle on the roster. Assert 0 failed and the per-oracle law floor.
# Roster: leadqualifier/ORACLES — first line `EXPECTED n`, then `path loads floor`.
set -euo pipefail
cd "$(dirname "$0")/.."
roster="leadqualifier/ORACLES"
expected=""
ran=0
while read -r a b c || [[ -n "${a:-}" ]]; do
  [[ -z "${a:-}" || "$a" == \#* ]] && continue
  if [[ "$a" == EXPECTED ]]; then
    expected="$b"
    continue
  fi
  path="$a"; loads="$b"; floor="$c"
  [[ -f "$path" ]] || { echo "missing $path"; exit 1; }
  load_count=$(grep -cE '^#load ' "$path" || true)
  if [[ "$load_count" -ne "$loads" ]]; then
    echo "loads $path: roster $loads, file $load_count"; exit 1
  fi
  out=$(dotnet fsi "$path" 2>/dev/null)
  echo "$out"
  echo "$out" | grep -q "0 failed" || { echo "failed: $path"; exit 1; }
  laws=$(echo "$out" | awk '/^LAWS / { print $2 }')
  if [[ -z "$laws" || "$laws" -lt "$floor" ]]; then
    echo "floor $path: need ≥ $floor, got ${laws:-none}"; exit 1
  fi
  ran=$((ran + 1))
done < "$roster"
if [[ -z "$expected" || "$ran" -ne "$expected" ]]; then
  echo "EXPECTED ${expected:-unset} oracles, ran $ran"; exit 1
fi
echo "oracles $ran ok"
