#!/usr/bin/env bash
# =============================================================================
# BotForge — Initial Deployment to EC2
# Run this ON the EC2 instance after setup-server.sh
# Clones repo, builds, configures systemd, starts all services
# =============================================================================
set -euo pipefail

APP_DIR="/opt/botforge/app"
REPO_URL="${REPO_URL:?Set REPO_URL (e.g., https://github.com/youruser/botforge.git)}"
DOMAIN="${DOMAIN:?Set DOMAIN (e.g., botforge.yourdomain.com)}"

echo "=== BotForge Initial Deployment ==="

# --- 1. Clone Repository ---
echo ""
echo "--- Cloning repository ---"
if [ -d "${APP_DIR}/.git" ]; then
    echo "Repo already exists, pulling latest..."
    sudo -u botforge git -C "$APP_DIR" pull origin main
else
    sudo -u botforge git clone "$REPO_URL" "$APP_DIR"
fi

# --- 2. Backend Setup ---
echo ""
echo "--- Setting up backend ---"
BACKEND_DIR="${APP_DIR}/botforge/backend"

# Create virtual environment
sudo -u botforge python3.12 -m venv "${BACKEND_DIR}/.venv"

# Install dependencies
sudo -u botforge "${BACKEND_DIR}/.venv/bin/pip" install --upgrade pip
sudo -u botforge "${BACKEND_DIR}/.venv/bin/pip" install -e "${BACKEND_DIR}"

# Copy environment file
if [ ! -f "${BACKEND_DIR}/.env" ]; then
    echo "IMPORTANT: Copy .env.production.template and fill in your values:"
    echo "  sudo -u botforge cp ${APP_DIR}/botforge/infra/aws/.env.production.template ${BACKEND_DIR}/.env"
    echo "  sudo -u botforge nano ${BACKEND_DIR}/.env"
    echo ""
    echo "Press Enter after configuring .env, or Ctrl+C to exit..."
    read -r
fi

# Run database migrations
echo "Running database migrations..."
sudo -u botforge bash -c "cd ${BACKEND_DIR} && .venv/bin/alembic upgrade head"

# --- 3. Frontend Setup ---
echo ""
echo "--- Setting up frontend ---"
FRONTEND_DIR="${APP_DIR}/frontend"

sudo -u botforge bash -c "cd ${FRONTEND_DIR} && npm ci"

# Create frontend .env.production (NEXT_PUBLIC_ vars are baked into the build)
# NOTE: SSM fetch script (fetch-ssm-secrets.sh) also writes this file on service restart.
# This block is a fallback for first-time setup only.
if [ ! -f "${FRONTEND_DIR}/.env.production" ]; then
    echo "NEXT_PUBLIC_API_URL=https://${DOMAIN}" | sudo -u botforge tee "${FRONTEND_DIR}/.env.production"
    echo "NEXT_PUBLIC_WS_URL=wss://${DOMAIN}" | sudo -u botforge tee -a "${FRONTEND_DIR}/.env.production"
fi

sudo -u botforge bash -c "cd ${FRONTEND_DIR} && npm run build"

# --- 4. Install systemd Services ---
echo ""
echo "--- Installing systemd services ---"
INFRA_DIR="${APP_DIR}/botforge/infra/aws"

sudo cp "${INFRA_DIR}/systemd/botforge-api.service" /etc/systemd/system/
sudo cp "${INFRA_DIR}/systemd/botforge-worker.service" /etc/systemd/system/
sudo cp "${INFRA_DIR}/systemd/botforge-frontend.service" /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable botforge-api botforge-worker botforge-frontend

# --- 5. Configure Redis ---
echo ""
echo "--- Configuring Redis ---"
sudo cp "${INFRA_DIR}/redis/redis-production.conf" /etc/redis/redis.conf
sudo systemctl restart redis-server

# --- 6. Configure Nginx ---
echo ""
echo "--- Configuring Nginx ---"
sudo cp "${INFRA_DIR}/nginx/botforge.conf" /etc/nginx/sites-available/botforge
sudo sed -i "s/DOMAIN_PLACEHOLDER/${DOMAIN}/g" /etc/nginx/sites-available/botforge
sudo ln -sf /etc/nginx/sites-available/botforge /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# --- 7. Start Services ---
echo ""
echo "--- Starting services ---"
sudo systemctl start botforge-api
sudo systemctl start botforge-worker
sudo systemctl start botforge-frontend

# Wait for services to start
sleep 5

# --- 8. Verify ---
echo ""
echo "--- Checking service status ---"
for svc in botforge-api botforge-worker botforge-frontend redis-server nginx; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || echo "inactive")
    echo "  ${svc}: ${STATUS}"
done

echo ""
echo "========================================="
echo "  BotForge Deployed Successfully"
echo "========================================="
echo ""
echo "Services running at:"
echo "  Backend API:  http://localhost:8000"
echo "  Frontend:     http://localhost:3000"
echo "  Nginx proxy:  http://${DOMAIN}"
echo ""
echo "Next steps:"
echo "  1. Run setup-ssl.sh to enable HTTPS"
echo "  2. Run verify-deployment.sh for full health check"
echo "========================================="
