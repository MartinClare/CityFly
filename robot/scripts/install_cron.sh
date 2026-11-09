#!/bin/bash
# Hourly recrawl. Full drafts ahead of FB windows.
# Facebook 10/day @ 07:30 / 12:00 / 18:00 HKT — 3 + 3 + 4 (attractiveness-ranked).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/venv/bin/python"
LOG="$ROOT/hk_city/data/cron.log"
HOURLY_SH="$ROOT/scripts/cron_hourly.sh"
FULL_SH="$ROOT/scripts/cron_full_draft.sh"
FB_PY="$ROOT/scripts/post_facebook.py"

# Linux cron respects CRON_TZ.
TZ_LINE="CRON_TZ=Asia/Hong_Kong"
HOURLY="15 * * * * $HOURLY_SH"
# Draft ~45–60 min before each FB slot so approve/export can finish
MORNING="30 6 * * * $FULL_SH morning"
LUNCH="0 11 * * * $FULL_SH noon"
EVENING="0 17 * * * $FULL_SH evening"
FB_MORNING="30 7 * * * cd \"$ROOT\" && \"$PY\" scripts/post_facebook.py --slot morning >> \"$LOG\" 2>&1"
FB_LUNCH="0 12 * * * cd \"$ROOT\" && \"$PY\" scripts/post_facebook.py --slot noon >> \"$LOG\" 2>&1"
FB_EVENING="0 18 * * * cd \"$ROOT\" && \"$PY\" scripts/post_facebook.py --slot evening >> \"$LOG\" 2>&1"

if [[ ! -x "$PY" ]]; then
  echo "Missing venv python at $PY — create venv first." >&2
  exit 1
fi

chmod +x "$HOURLY_SH" "$FULL_SH"

EXISTING="$(crontab -l 2>/dev/null || true)"
# Drop prior City Sight jobs (old inline python and new wrappers).
CLEAN="$(printf "%s\n" "$EXISTING" \
  | grep -v "run_daily.py hk_city" \
  | grep -v "post_facebook.py" \
  | grep -v "cron_hourly.sh" \
  | grep -v "cron_full_draft.sh" \
  | grep -v "^CRON_TZ=" \
  || true)"
MERGED="$(printf "%s\n" "$TZ_LINE"; printf "%s\n" "$CLEAN"; echo "$HOURLY"; echo "$MORNING"; echo "$LUNCH"; echo "$EVENING"; echo "$FB_MORNING"; echo "$FB_LUNCH"; echo "$FB_EVENING")"
printf "%s\n" "$MERGED" | crontab -
echo "Installed cron (HKT):"
echo "  $HOURLY   # rank only"
echo "  $MORNING  # WRITE articles"
echo "  $LUNCH    # WRITE articles"
echo "  $EVENING  # WRITE articles"
echo "  $FB_MORNING"
echo "  $FB_LUNCH"
echo "  $FB_EVENING"
