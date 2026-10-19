#!/bin/bash
# Full desk run: collect, rank, and WRITE article packs.
# Used by morning / noon / evening cron. Never passes --hourly.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/venv/bin/python"
LOG="$ROOT/hk_city/data/cron.log"
LOCK="$ROOT/hk_city/data/run_daily.lock"
SLOT="${1:-full}"
mkdir -p "$(dirname "$LOG")" "$(dirname "$LOCK")"

{
  echo "=== FULL DRAFT START slot=${SLOT} $(date '+%Y-%m-%dT%H:%M:%S%z') ==="
  # Wait for an hourly recrawl to finish (up to 2h) so noon/evening still draft.
  if ! flock -w 7200 200; then
    echo "FULL DRAFT FAILED slot=${SLOT} — could not acquire run_daily lock"
    echo "=== FULL DRAFT END slot=${SLOT} $(date '+%Y-%m-%dT%H:%M:%S%z') lock_timeout ==="
    exit 1
  fi
  cd "$ROOT"
  # Explicit: no --hourly, no --skip-report — must write articles.
  "$PY" run_daily.py hk_city
  echo "=== FULL DRAFT END slot=${SLOT} $(date '+%Y-%m-%dT%H:%M:%S%z') ==="
} 200>"$LOCK" >>"$LOG" 2>&1
