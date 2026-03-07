#!/usr/bin/env bash
# =============================================================================
# BotForge — Update Application (subsequent deploys)
# Run this ON the EC2 instance to deploy latest code
# =============================================================================
set -euo pipefail

APP_DIR="/opt/botforge/app"
BACKEND_DIR="${APP_DIR}/botforge/backend"
FRONTEND_DIR="${APP_DIR}/frontend"

echo "=== BotForge Update ==="

# --- 1. Pull Latest Code ---
echo "--- Pulling latest code ---"
sudo -u botforge git -C "$APP_DIR" pull origin main

# --- 2. Backend Update ---
echo "--- Updating backend ---"
sudo -u botforge "${BACKEND_DIR}/.venv/bin/pip" install -e "${BACKEND_DIR}"
sudo -u botforge bash -c "cd ${BACKEND_DIR} && .venv/bin/alembic upgrade head"

# --- 3. Frontend Update ---
# Runs as root because botforge user cannot access npm (symlink into
# ubuntu's home dir with 700 permissions). Next.js reads NEXT_PUBLIC_API_URL
# from the .env.production file already present on the server.
echo "--- Updating frontend ---"
sudo bash -c "cd ${FRONTEND_DIR} && npm ci --production=false && npm run build && npm prune --production"
sudo chown -R botforge:botforge "${FRONTEND_DIR}"

# --- 4. Restart Services ---
echo "--- Restarting services ---"
sudo systemctl restart botforge-api
sudo systemctl restart botforge-worker
sudo systemctl restart botforge-frontend

# Wait for services
sleep 5

# --- 5. Health Check ---
echo "--- Health check ---"
for svc in botforge-api botforge-worker botforge-frontend; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || echo "inactive")
    echo "  ${svc}: ${STATUS}"
done

API_STATUS=$(curl -sf http://localhost:8000/health | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null || echo "unreachable")
echo "  API health: ${API_STATUS}"

echo ""
echo "Update complete!"
