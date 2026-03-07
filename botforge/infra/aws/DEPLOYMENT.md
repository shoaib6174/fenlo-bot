# BotForge AWS Deployment Guide

Complete step-by-step guide for deploying BotForge on AWS Free Tier ($0/month).

## Architecture

```
Namecheap DNS (A record) --> Elastic IP
                                 |
                        EC2 m7i-flex.large (2 vCPU, 8GB RAM)
                        +-- Nginx (reverse proxy + SSL)
                        +-- FastAPI backend (:8000, 4 workers)
                        +-- Next.js frontend (:3000)
                        +-- ARQ worker (background jobs)
                        +-- Redis (local, 256MB max)
                                 |
                        RDS db.t3.micro (PostgreSQL 16, 20GB)

                        S3 Bucket (file uploads, 5GB)
```

**Cost: $0/month** — all within AWS 12-month free tier (EC2 750hrs, RDS 750hrs, S3 5GB).

## Prerequisites

- AWS account with free tier eligibility
- AWS CLI installed and configured (`aws configure`)
- Domain name (e.g., from Namecheap)
- Git repository with BotForge code
- API keys: Groq (free) and optionally OpenAI

## Step 1: Create AWS Resources

```bash
export DB_PASSWORD="your-secure-password"  # pragma: allowlist secret
export AWS_REGION="us-east-1"

./setup-aws-resources.sh
```

This creates:
- EC2 t3.micro instance (Ubuntu 22.04, 20GB gp3)
- Elastic IP address
- RDS db.t3.micro (PostgreSQL 16, 20GB, private)
- S3 bucket (private, encrypted)
- Security groups (web: 80/443/22, rds: 5432 from EC2 only)
- IAM role for EC2 → S3 access
- SSH key pair

Save the output — you'll need the Elastic IP and key pair file.

## Step 2: Configure DNS

In your Namecheap dashboard:
1. Go to **Domain List** → your domain → **Advanced DNS**
2. Add an **A Record**:
   - Host: `@` (or subdomain like `app`)
   - Value: your Elastic IP address
   - TTL: Automatic
3. Wait for DNS propagation (5-30 minutes)

Verify: `dig yourdomain.com` should show the Elastic IP.

## Step 3: Setup Server

SSH into the EC2 instance:

```bash
ssh -i botforge-key.pem ubuntu@<ELASTIC_IP>
```

Run the server setup script:

```bash
# Upload and run setup script
sudo bash /path/to/setup-server.sh
```

This installs Python 3.12, Node 20, Redis, Nginx, Certbot, fail2ban, UFW, and creates 1GB swap.

## Step 4: Deploy Application

```bash
export REPO_URL="https://github.com/youruser/botforge.git"
export DOMAIN="yourdomain.com"

sudo bash /path/to/deploy.sh
```

When prompted, configure the `.env` file with your production values using the template at `botforge/infra/aws/.env.production.template`.

## Step 5: Enable SSL (HTTPS)

```bash
export DOMAIN="yourdomain.com"
export EMAIL="your@email.com"

sudo bash /path/to/setup-ssl.sh
```

## Step 6: Verify Deployment

```bash
export DOMAIN="yourdomain.com"
bash verify-deployment.sh
```

Expected results:
- All 5 systemd services: active
- Health endpoints: returning `{"status": "ok"}`
- SSL: working with HTTPS redirect
- Frontend: HTTP 200
- Demo login: returns access token
- Memory: < 800MB used

## Monitoring & Maintenance

### View logs

```bash
# Service logs
sudo journalctl -u botforge-api -f
sudo journalctl -u botforge-worker -f
sudo journalctl -u botforge-frontend -f

# Nginx access/error logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Service management

```bash
# Check status
sudo systemctl status botforge-api botforge-worker botforge-frontend

# Restart a service
sudo systemctl restart botforge-api

# View memory usage
free -h
```

### Database backup

```bash
# Manual backup
sudo bash /path/to/backup-db.sh

# Setup daily backup cron (3 AM)
echo "0 3 * * * /opt/botforge/app/botforge/infra/aws/backup-db.sh" | sudo crontab -
```

### Update application

```bash
# Manual update
sudo bash /path/to/update-app.sh

# Or pushes to main auto-deploy via GitHub Actions
```

## Troubleshooting

### Service won't start

```bash
# Check logs for the failing service
sudo journalctl -u botforge-api --no-pager -n 50

# Common issues:
# - Missing .env file
# - Database connection refused (check RDS security group)
# - Port already in use
```

### Out of memory

```bash
# Check memory
free -h

# Check which service uses most memory
sudo systemctl status botforge-api botforge-worker botforge-frontend | grep Memory

# If OOM, restart services (systemd MemoryMax will auto-kill if exceeded)
sudo systemctl restart botforge-api botforge-worker botforge-frontend
```

### Can't connect to RDS

- Ensure RDS security group allows port 5432 from EC2's security group
- Ensure RDS is in the same VPC as EC2
- Check RDS is in "available" state: `aws rds describe-db-instances --db-instance-identifier botforge-db`

### SSL certificate issues

```bash
# Check certificate status
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal

# Test auto-renewal
sudo certbot renew --dry-run
```

## Free Tier Limits

| Service | Free Tier Limit | Our Usage |
|---------|----------------|-----------|
| EC2 t3.micro | 750 hrs/month | ~730 hrs (1 instance 24/7) |
| RDS db.t3.micro | 750 hrs/month | ~730 hrs (1 instance 24/7) |
| S3 | 5 GB storage | File uploads |
| Data transfer | 100 GB/month out | Low traffic portfolio site |

**Important**: Free tier expires 12 months after AWS account creation. Set up AWS Budgets alerts to monitor costs.

## GitHub Secrets for CI/CD

Set these in your repo's **Settings → Secrets → Actions**:

| Secret | Value |
|--------|-------|
| `EC2_HOST` | Your Elastic IP address |
| `EC2_SSH_KEY` | Contents of `botforge-key.pem` |
