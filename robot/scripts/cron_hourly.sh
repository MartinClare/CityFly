#!/bin/bash
# Recrawl + rank only. Never drafts articles.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/venv/bin/python"
LOG="$ROOT/hk_city/data/cron.log"
LOCK="$ROOT/hk_city/data/run_daily.lock"
mkdir -p "$(dirname "$LOG")" "$(dirname "$LOCK")"

{
  echo "=== HOURLY START $(date '+%Y-%m-%dT%H:%M:%S%z') ==="
  # Skip if a full draft (or another hourly) is already running.
  if ! flock -n 200; then
    echo "HOURLY skipped — run_daily lock busy"
    echo "=== HOURLY END $(date '+%Y-%m-%dT%H:%M:%S%z') skipped ==="
    exit 0
  fi
  cd "$ROOT"
  "$PY" run_daily.py hk_city --hourly
  echo "=== HOURLY END $(date '+%Y-%m-%dT%H:%M:%S%z') ==="
} 200>"$LOCK" >>"$LOG" 2>&1
