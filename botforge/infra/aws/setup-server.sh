#!/usr/bin/env bash
# =============================================================================
# BotForge — EC2 Server Setup (Ubuntu 22.04)
# Run this ON the EC2 instance after setup-aws-resources.sh
# Installs: Python 3.12, Node 20, Redis, Nginx, Certbot, swap, firewall
# =============================================================================
set -euo pipefail

echo "=== BotForge Server Setup ==="

# --- 1. Create 1GB Swap (safety net for m7i-flex.large 8GB RAM) ---
echo ""
echo "--- Creating 1GB swap file ---"
if [ ! -f /swapfile ]; then
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    # Tune swappiness for low-memory server
    echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
    sudo sysctl -p
    echo "Swap created (1GB)"
else
    echo "Swap already exists"
fi

# --- 2. System Updates ---
echo ""
echo "--- Updating system packages ---"
sudo apt-get update -y
sudo apt-get upgrade -y

# --- 3. Python 3.12 ---
echo ""
echo "--- Installing Python 3.12 ---"
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update -y
sudo apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc

# --- 4. Node.js 20 ---
echo ""
echo "--- Installing Node.js 20 ---"
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# --- 5. Redis ---
echo ""
echo "--- Installing Redis ---"
sudo apt-get install -y redis-server
sudo cp /opt/botforge/infra/aws/redis/redis-production.conf /etc/redis/redis.conf 2>/dev/null || true
sudo systemctl enable redis-server

# --- 6. Nginx ---
echo ""
echo "--- Installing Nginx ---"
sudo apt-get install -y nginx
sudo systemctl enable nginx

# --- 7. Certbot (Let's Encrypt) ---
echo ""
echo "--- Installing Certbot ---"
sudo apt-get install -y certbot python3-certbot-nginx

# --- 8. Fail2ban ---
echo ""
echo "--- Installing Fail2ban ---"
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# --- 9. UFW Firewall ---
echo ""
echo "--- Configuring UFW Firewall ---"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# --- 10. PostgreSQL Client (for RDS access) ---
echo ""
echo "--- Installing PostgreSQL client ---"
sudo apt-get install -y postgresql-client

# --- 11. Create application user and directory ---
echo ""
echo "--- Creating botforge user and directories ---"
sudo useradd --system --shell /bin/bash --home /opt/botforge --create-home botforge 2>/dev/null || true
sudo mkdir -p /opt/botforge/{app,logs,uploads}
sudo chown -R botforge:botforge /opt/botforge

# --- 12. Install build tools ---
echo ""
echo "--- Installing build tools ---"
sudo apt-get install -y build-essential libffi-dev libpq-dev

# --- Cleanup ---
sudo apt-get autoremove -y
sudo apt-get clean

echo ""
echo "========================================="
echo "  Server Setup Complete"
echo "========================================="
echo ""
echo "Installed:"
echo "  Python: $(python3 --version)"
echo "  Node:   $(node --version)"
echo "  npm:    $(npm --version)"
echo "  Redis:  $(redis-server --version)"
echo "  Nginx:  $(nginx -v 2>&1)"
echo "  Swap:   $(swapon --show)"
echo ""
echo "Next step: Run deploy.sh to deploy the application"
echo "========================================="
