#!/usr/bin/env bash
# =============================================================================
# BotForge — Hotfix: Fix WebSocket through HTTPS nginx
# Run this ON the EC2 instance to fix WSS (WebSocket over TLS)
#
# Problem: The original setup-ssl.sh used a fragile sed-uncomment approach
# that could leave the HTTPS server block missing WebSocket upgrade headers.
#
# Fix: Replaces the nginx config with botforge-ssl.conf which has proper
# WebSocket support (map $http_upgrade, proxy_buffering off, etc.)
# =============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/botforge/app}"
INFRA_DIR="${APP_DIR}/botforge/infra/aws"
NGINX_CONF="/etc/nginx/sites-available/botforge"

# Auto-detect domain from existing config
DOMAIN=$(grep -oP 'server_name \K[^;]+' "$NGINX_CONF" | head -1 | tr -d ' ')
if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "DOMAIN_PLACEHOLDER" ]; then
    DOMAIN="${DOMAIN:?Could not auto-detect domain. Set DOMAIN env var.}"
fi

echo "=== BotForge WebSocket Hotfix ==="
echo "Domain: ${DOMAIN}"
echo ""

# Verify SSL cert exists
if [ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    echo "ERROR: SSL certificate not found at /etc/letsencrypt/live/${DOMAIN}/"
    echo "Run setup-ssl.sh first to obtain an SSL certificate."
    exit 1
fi

# Verify the new config template exists
if [ ! -f "${INFRA_DIR}/nginx/botforge-ssl.conf" ]; then
    echo "ERROR: botforge-ssl.conf not found. Pull the latest code first:"
    echo "  sudo -u botforge git -C ${APP_DIR} pull origin main"
    exit 1
fi

# Back up current config
echo "--- Backing up current nginx config ---"
sudo cp "$NGINX_CONF" "${NGINX_CONF}.bak.$(date +%Y%m%d-%H%M%S)"

# Install new config
echo "--- Installing fixed nginx config with WebSocket support ---"
sudo cp "${INFRA_DIR}/nginx/botforge-ssl.conf" "$NGINX_CONF"
sudo sed -i "s/DOMAIN_PLACEHOLDER/${DOMAIN}/g" "$NGINX_CONF"

# Test config
echo ""
echo "--- Testing nginx config ---"
if sudo nginx -t; then
    echo ""
    echo "--- Reloading nginx ---"
    sudo systemctl reload nginx
    echo ""
    echo "========================================="
    echo "  WebSocket Fix Applied"
    echo "========================================="
    echo "  wss://${DOMAIN}/api/v1/chat/stream is now available"
    echo ""
    echo "  Verify with:"
    echo "    curl -i -N -H 'Connection: Upgrade' -H 'Upgrade: websocket' \\"
    echo "      -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \\"
    echo "      https://${DOMAIN}/api/v1/chat/stream"
    echo "========================================="
else
    echo ""
    echo "ERROR: nginx config test failed. Restoring backup..."
    LATEST_BACKUP=$(ls -t "${NGINX_CONF}.bak."* 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        sudo cp "$LATEST_BACKUP" "$NGINX_CONF"
        sudo nginx -t && sudo systemctl reload nginx
        echo "Backup restored. No changes applied."
    fi
    exit 1
fi
