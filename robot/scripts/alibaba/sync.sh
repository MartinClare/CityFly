#!/bin/bash
# Push robot/ code to the HK ECS app root, or pull drafts back to this Mac.
# Local monorepo: City Fly/robot/ → remote /opt/cityfly-robot/ (flat; no nested robot/).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE="$(cd "$(dirname "$0")" && pwd)/.state/host.env"
DO_BOOTSTRAP=0
DO_PULL=0
WITH_DATA=0

for arg in "$@"; do
  case "$arg" in
    --bootstrap) DO_BOOTSTRAP=1 ;;
    --pull) DO_PULL=1 ;;
    --with-data) WITH_DATA=1 ;;
    *) echo "Usage: $0 [--bootstrap|--pull|--with-data]" >&2; exit 1 ;;
  esac
done

if [[ ! -f "$STATE" ]]; then
  echo "No host yet. Run scripts/alibaba/provision.sh after aliyun configure." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$STATE"
HOST="${CITYFLY_HOST:?}"
USER="${CITYFLY_USER:-root}"
REMOTE="${USER}@${HOST}"
APP="${CITYFLY_APP:-/opt/cityfly-robot}"

if [[ "$DO_PULL" -eq 1 ]]; then
  mkdir -p "$ROOT/hk_city/data"
  rsync -az --exclude cron.log "${REMOTE}:${APP}/hk_city/data/" "$ROOT/hk_city/data/"
  echo "Pulled drafts/reports from $HOST"
  exit 0
fi

if [[ ! -f "$ROOT/.env" ]]; then
  echo "Need $ROOT/.env on this Mac (OPENROUTER_API_KEY, KIE_API_KEY)." >&2
  exit 1
fi

ssh -o StrictHostKeyChecking=accept-new "$REMOTE" "mkdir -p $APP"
RSYNC_EXCLUDES=(
  --exclude venv/
  --exclude .cursor/
  --exclude .git/
  --exclude .DS_Store
  --exclude scripts/alibaba/.state/
  --exclude hk_city/data/cron.log
  --exclude hk_city/data/raw/
  --exclude hk_city/data/processed/
)
if [[ "$WITH_DATA" -eq 0 ]]; then
  RSYNC_EXCLUDES+=(--exclude hk_city/data/)
fi
rsync -az "${RSYNC_EXCLUDES[@]}" "$ROOT/" "$REMOTE:$APP/"
scp -q "$ROOT/.env" "$REMOTE:$APP/.env"

if [[ "$DO_BOOTSTRAP" -eq 1 ]]; then
  ssh "$REMOTE" "CITYFLY_APP='$APP' bash $APP/scripts/alibaba/bootstrap.sh"
fi
echo "Synced to $REMOTE:$APP"
