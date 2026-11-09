#!/bin/bash
# Hourly recrawl. Full article drafts at 07:30, 12:30, and 18:30 HKT.
# Facebook link posts shortly after each draft window.
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
MORNING="30 7 * * * $FULL_SH morning"
LUNCH="30 12 * * * $FULL_SH noon"
EVENING="30 18 * * * $FULL_SH evening"
FB_MORNING="45 8 * * * cd \"$ROOT\" && \"$PY\" scripts/post_facebook.py >> \"$LOG\" 2>&1"
FB_LUNCH="45 13 * * * cd \"$ROOT\" && \"$PY\" scripts/post_facebook.py >> \"$LOG\" 2>&1"
FB_EVENING="45 19 * * * cd \"$ROOT\" && \"$PY\" scripts/post_facebook.py >> \"$LOG\" 2>&1"

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
