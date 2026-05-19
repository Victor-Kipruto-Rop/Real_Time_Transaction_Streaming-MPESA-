#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/Real_Time_Transaction_Streaming-MPESA-}"
DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"
ADMIN_CIDR="${ADMIN_CIDR:-}"
PUBLIC_IP="${PUBLIC_IP:-54.193.78.115}"
TEMPLATE="$PROJECT_DIR/deploy/nginx/mpesa-streaming-https.conf.template"
NGINX_CONF="/etc/nginx/conf.d/mpesa-streaming.conf"
WEBROOT="/var/www/certbot"

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "Usage: DOMAIN=mpesa.example.com EMAIL=admin@example.com ADMIN_CIDR=x.x.x.x/32 $0" >&2
  exit 2
fi

if [[ -z "$ADMIN_CIDR" ]]; then
  ADMIN_CIDR="$(curl -fsS https://checkip.amazonaws.com)/32"
fi

resolved_ip="$(getent ahostsv4 "$DOMAIN" | awk '{print $1; exit}')"
if [[ "$resolved_ip" != "$PUBLIC_IP" ]]; then
  echo "DNS for $DOMAIN resolves to '${resolved_ip:-<none>}', expected $PUBLIC_IP" >&2
  echo "Create an A record for $DOMAIN -> $PUBLIC_IP and rerun this script." >&2
  exit 3
fi

sudo dnf install -y nginx certbot python3-certbot-nginx
sudo mkdir -p "$WEBROOT"

sudo tee /etc/nginx/conf.d/mpesa-acme.conf >/dev/null <<NGINX
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root $WEBROOT;
    }

    location / {
        return 200 "ACME bootstrap for $DOMAIN\n";
        add_header Content-Type text/plain;
    }
}
NGINX

sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx

sudo certbot certonly \
  --webroot \
  --webroot-path "$WEBROOT" \
  --domain "$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos \
  --non-interactive

sudo sed \
  -e "s/__DOMAIN__/$DOMAIN/g" \
  -e "s#__ADMIN_CIDR__#$ADMIN_CIDR#g" \
  "$TEMPLATE" | sudo tee "$NGINX_CONF" >/dev/null
sudo rm -f /etc/nginx/conf.d/mpesa-acme.conf
sudo nginx -t

cd "$PROJECT_DIR"
python3 - <<PY
from pathlib import Path

path = Path(".env")
values = {}
lines = path.read_text().splitlines()
for raw in lines:
    if raw.strip() and not raw.strip().startswith("#") and "=" in raw:
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip()

values["CALLBACK_URL"] = "https://$DOMAIN/webhook/stk/callback"
values["GRAFANA_URL"] = "https://$DOMAIN/grafana"
values["GRAFANA_SERVE_FROM_SUB_PATH"] = "true"

seen = set()
output = []
for raw in lines:
    if raw.strip().startswith("#"):
        output.append(raw)
        continue
    if "=" not in raw:
        continue
    key = raw.split("=", 1)[0].strip()
    if key in values and key not in seen:
        output.append(f"{key}={values[key]}")
        seen.add(key)
for key in sorted(values):
    if key not in seen:
        output.append(f"{key}={values[key]}")
path.write_text("\\n".join(output) + "\\n")
path.chmod(0o600)
PY

docker compose up -d --force-recreate grafana webhook-receiver kafka-consumer
sudo systemctl reload nginx
sudo systemctl status certbot-renew.timer --no-pager || true

echo "HTTPS enabled:"
echo "  https://$DOMAIN/health"
echo "  https://$DOMAIN/webhook/c2b/confirmation"
echo "  https://$DOMAIN/grafana/"
