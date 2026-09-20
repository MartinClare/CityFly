#!/bin/bash
# Snapshot the Hong Kong robot: cron, disk, last log, latest drafts.
set -euo pipefail
STATE="$(cd "$(dirname "$0")" && pwd)/.state/host.env"
if [[ ! -f "$STATE" ]]; then
  echo "No host.env — robot not linked yet." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$STATE"
APP="${CITYFLY_APP:-/opt/cityfly-robot}"
ssh -o ConnectTimeout=8 -o BatchMode=yes "${CITYFLY_USER:-root}@${CITYFLY_HOST}" bash -s -- "$APP" <<'EOS'
APP="$1"
echo "HOST $(hostname)  $(date)"
echo "TZ $(timedatectl 2>/dev/null | awk -F': ' '/Time zone/{print $2}' || date +%Z)"
uptime -p
df -h / | tail -1
echo
echo "=== cron ==="
crontab -l 2>/dev/null | grep -E 'CRON_TZ|hk_city' || echo "(no city-fly cron)"
echo
echo "=== last log ==="
if [[ -f "$APP/hk_city/data/cron.log" ]]; then
  tail -n 40 "$APP/hk_city/data/cron.log"
else
  echo "(no cron.log yet — first hourly run is :15)"
fi
echo
echo "=== latest drafts ==="
ls -1t "$APP/hk_city/data/drafts"/*/ 2>/dev/null | head -20 || echo "(no drafts)"
EOS
