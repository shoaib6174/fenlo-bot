#!/usr/bin/env bash
# =============================================================================
# BotForge — SSL Setup via Let's Encrypt + Certbot
# Run this AFTER deploy.sh and DNS is pointing to the Elastic IP
#
# 1. Obtains SSL certificate via certbot (webroot mode)
# 2. Replaces the HTTP-only nginx config with the full HTTPS config
#    (botforge-ssl.conf has proper WebSocket upgrade headers)
# 3. Tests and reloads nginx
# =============================================================================
set -euo pipefail

DOMAIN="${DOMAIN:?Set DOMAIN (e.g., botforge.yourdomain.com)}"
EMAIL="${EMAIL:?Set EMAIL for Let's Encrypt notifications}"
APP_DIR="${APP_DIR:-/opt/botforge/app}"
INFRA_DIR="${APP_DIR}/botforge/infra/aws"
NGINX_CONF="/etc/nginx/sites-available/botforge"

echo "=== BotForge SSL Setup ==="
echo "Domain: ${DOMAIN}"
echo "Email:  ${EMAIL}"

# --- 1. Obtain SSL certificate (certonly — does NOT modify nginx config) ---
echo ""
echo "--- Obtaining SSL certificate ---"
sudo certbot certonly --webroot \
    -w /var/www/html \
    -d "$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL"

# --- 2. Download SSL params if not present ---
if [ ! -f /etc/letsencrypt/options-ssl-nginx.conf ]; then
    echo "--- Downloading SSL params ---"
    sudo curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf \
        -o /etc/letsencrypt/options-ssl-nginx.conf
fi

if [ ! -f /etc/letsencrypt/ssl-dhparams.pem ]; then
    sudo curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem \
        -o /etc/letsencrypt/ssl-dhparams.pem
fi

# --- 3. Install the HTTPS nginx config (replaces HTTP-only config) ---
echo ""
echo "--- Installing HTTPS nginx config with WebSocket support ---"

# Back up the current config
if [ -f "$NGINX_CONF" ]; then
    sudo cp "$NGINX_CONF" "${NGINX_CONF}.pre-ssl.bak"
    echo "  Backed up current config to ${NGINX_CONF}.pre-ssl.bak"
fi

# Copy the SSL config template and substitute domain
sudo cp "${INFRA_DIR}/nginx/botforge-ssl.conf" "$NGINX_CONF"
sudo sed -i "s/DOMAIN_PLACEHOLDER/${DOMAIN}/g" "$NGINX_CONF"
echo "  Installed botforge-ssl.conf with domain: ${DOMAIN}"

# --- 4. Test and reload ---
echo ""
echo "--- Testing nginx config ---"
sudo nginx -t
sudo systemctl reload nginx

# --- 5. Verify auto-renewal ---
echo ""
echo "--- Testing auto-renewal ---"
sudo certbot renew --dry-run

echo ""
echo "========================================="
echo "  SSL Setup Complete"
echo "========================================="
echo "  https://${DOMAIN} is now live"
echo "  WebSocket (wss://) is enabled"
echo "  Certificate auto-renews via certbot timer"
echo "========================================="
