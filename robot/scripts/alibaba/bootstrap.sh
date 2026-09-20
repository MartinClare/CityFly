#!/bin/bash
# Runs on the Hong Kong ECS after the first rsync.
set -euo pipefail
APP="${CITYFLY_APP:-/opt/cityfly-robot}"
export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y python3 python3-venv python3-pip rsync ca-certificates
# 22.04 ships 3.10; that is enough for the desk. Do not block on 3.12.
if command -v timedatectl >/dev/null; then
  timedatectl set-timezone Asia/Hong_Kong
fi
mkdir -p "$APP"
cd "$APP"
if [[ ! -f .env ]]; then
  echo "Missing $APP/.env — sync it from the Mac first." >&2
  exit 1
fi
if [[ ! -d venv ]]; then
  python3 -m venv venv
fi
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt
./scripts/install_cron.sh
if [[ -f "$APP/scripts/alibaba/city-fly-desk.service" ]]; then
  sed "s|/opt/city-fly|$APP|g; s|/opt/cityfly-robot|$APP|g" \
    "$APP/scripts/alibaba/city-fly-desk.service" >/etc/systemd/system/city-fly-desk.service
  systemctl daemon-reload
  systemctl enable --now city-fly-desk.service
fi
echo "Robot ready. TZ=$(date +%Z) cron:"
crontab -l | grep cityfly || crontab -l | grep hk_city
