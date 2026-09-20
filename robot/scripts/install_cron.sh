#!/bin/bash
# Hourly recrawl + 07:30 daily draft of new stories only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/venv/bin/python"
LOG="$ROOT/hk_city/data/cron.log"
# Linux cron respects CRON_TZ. macOS cron follows the system timezone.
TZ_LINE="CRON_TZ=Asia/Hong_Kong"
HOURLY="15 * * * * cd \"$ROOT\" && \"$PY\" run_daily.py hk_city --hourly >> \"$LOG\" 2>&1"
DAILY="30 7 * * * cd \"$ROOT\" && \"$PY\" run_daily.py hk_city >> \"$LOG\" 2>&1"

if [[ ! -x "$PY" ]]; then
  echo "Missing venv python at $PY — create venv first." >&2
  exit 1
fi

EXISTING="$(crontab -l 2>/dev/null || true)"
CLEAN="$(printf "%s\n" "$EXISTING" | grep -v "run_daily.py hk_city" | grep -v "^CRON_TZ=" || true)"
if echo "$EXISTING" | grep -q '^CRON_TZ='; then
  MERGED="$(printf "%s\n" "$TZ_LINE"; printf "%s\n" "$CLEAN"; echo "$HOURLY"; echo "$DAILY")"
else
  MERGED="$(printf "%s\n" "$TZ_LINE"; printf "%s\n" "$CLEAN"; echo "$HOURLY"; echo "$DAILY")"
fi
printf "%s\n" "$MERGED" | crontab -
echo "Installed cron:"
echo "$HOURLY"
echo "$DAILY"
