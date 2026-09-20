#!/bin/bash
# Install Caddy on the HK robot and proxy HTTPS → desk :8787.
# Requires: CADDY_DOMAIN in /opt/cityfly-robot/.env (e.g. desk.example.com)
# DNS: A record for that hostname → this server's public IP
# Security group: allow TCP 80 and 443 (worldwide or your IP)
set -euo pipefail

APP="${CITYFLY_APP:-/opt/cityfly-robot}"
ENV_FILE="$APP/.env"
CADDYFILE_SRC="$APP/scripts/alibaba/Caddyfile"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
set -a
# shellcheck disable=SC1091
source "$ENV_FILE"
set +a

DOMAIN="${CADDY_DOMAIN:-}"
if [[ -z "$DOMAIN" ]]; then
  echo "Set CADDY_DOMAIN in $ENV_FILE first, e.g. CADDY_DOMAIN=desk.yourdomain.com" >&2
  exit 1
fi

if ! command -v caddy >/dev/null 2>&1; then
  echo "Installing Caddy..."
  apt-get update -y
  apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  apt-get update -y
  apt-get install -y caddy
fi

mkdir -p /var/log/caddy
chown caddy:caddy /var/log/caddy

# Desk only listens locally once Caddy is in front
if grep -q '^DESK_BIND=' "$ENV_FILE"; then
  sed -i 's/^DESK_BIND=.*/DESK_BIND=127.0.0.1/' "$ENV_FILE"
else
  echo 'DESK_BIND=127.0.0.1' >> "$ENV_FILE"
fi

# Systemd unit for desk should not force 0.0.0.0 when behind Caddy
UNIT=/etc/systemd/system/city-fly-desk.service
if [[ -f "$UNIT" ]]; then
  sed -i 's/Environment=DESK_BIND=0.0.0.0/Environment=DESK_BIND=127.0.0.1/' "$UNIT" || true
fi

install -m 644 "$CADDYFILE_SRC" /etc/caddy/Caddyfile
# Inject domain via systemd drop-in for caddy
mkdir -p /etc/systemd/system/caddy.service.d
cat >/etc/systemd/system/caddy.service.d/cityfly.conf <<EOF
[Service]
Environment=CADDY_DOMAIN=$DOMAIN
EnvironmentFile=-$ENV_FILE
EOF

systemctl daemon-reload
systemctl enable --now caddy
systemctl restart city-fly-desk
systemctl restart caddy
sleep 1

echo "Caddy domain: https://$DOMAIN"
echo "Desk bind: $(grep '^DESK_BIND=' "$ENV_FILE")"
systemctl is-active caddy
systemctl is-active city-fly-desk
ss -lntp | grep -E ':80|:443|:8787' || true
echo
echo "DNS check: dig +short $DOMAIN"
dig +short "$DOMAIN" || true
echo
echo "If TLS fails: open SG TCP 80+443, wait for DNS A → this host, then: systemctl restart caddy"
