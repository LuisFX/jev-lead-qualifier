#!/usr/bin/env bash
# Loads API keys from the environment or ./.env (never printed) and runs a First Read command.
#
#   ./run.sh serve            # FastAPI + UI on http://127.0.0.1:8780
#   ./run.sh dataset          # regenerate data/leads/, data/gold.json, data/crm.json
#   ./run.sh score            # score all leads on the CLI (real Jev), print tier accuracy vs gold
#   ./run.sh test             # unit tests (mocked Jev, offline)
#   ./run.sh test-all         # + integration tests against the real API (~60 requests, < 1 cent)
#   ./run.sh shots            # Playwright screenshots → reports/ui/
#   ./run.sh questions        # dump the question set built from data/icp.json
#   ./run.sh oracles          # execute every oracle on the roster (0 failed, law floor)
set -euo pipefail
cd "$(dirname "$0")"

# Keys come from the environment or a local, gitignored .env (cp .env.example .env).
# Variables already set in the environment win. Values are never printed.
load_env_file() {
  local line key val
  [[ -f "$1" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]] || continue
    key="${BASH_REMATCH[1]}"; val="${BASH_REMATCH[2]}"
    val="${val%%[[:space:]]#*}"
    val="${val%"${val##*[![:space:]]}"}"
    val="${val#\"}"; val="${val%\"}"; val="${val#\'}"; val="${val%\'}"
    if [[ "$val" == your-* ]]; then continue; fi
    if [[ -z "${!key:-}" && -n "$val" ]]; then export "$key=$val"; fi
  done < "$1"
  return 0
}
load_env_file .env
export TYPESAFE_API_KEY="${TYPESAFE_API_KEY:-${JEV_API_KEY:-}}"
export PYTHONUNBUFFERED=1

cmd="${1:-serve}"
shift || true
case "$cmd" in
  serve)
    exec uv run uvicorn leadqualifier.server:app --host 127.0.0.1 --port "${PORT:-8780}" "$@" ;;
  dataset)
    exec uv run python scripts/make_dataset.py "$@" ;;
  score)
    exec uv run python -m leadqualifier.cli score "$@" ;;
  test)
    exec uv run pytest -m "not integration" "$@" ;;
  test-all)
    exec uv run pytest "$@" ;;
  shots)
    exec uv run python scripts/ui_screenshots.py "$@" ;;
  questions)
    exec uv run python -m leadqualifier.cli questions "$@" ;;
  oracles)
    exec ./scripts/check_oracles.sh "$@" ;;
  python)
    exec uv run python "$@" ;;
  *)
    echo "unknown command: $cmd"; exit 1 ;;
esac
