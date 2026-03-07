# BotForge Infrastructure

## Overview

BotForge runs on AWS Free Tier ($0/month) using native installs on a single EC2 instance.

```
botforge/infra/
├── aws/                         # AWS deployment scripts & configs
│   ├── DEPLOYMENT.md            # Full deployment guide
│   ├── setup-aws-resources.sh   # Create EC2, RDS, S3, security groups
│   ├── setup-server.sh          # Install runtime dependencies on EC2
│   ├── deploy.sh                # Initial app deployment
│   ├── update-app.sh            # Subsequent deploys (git pull + restart)
│   ├── setup-ssl.sh             # Let's Encrypt SSL via Certbot
│   ├── backup-db.sh             # pg_dump RDS to S3
│   ├── verify-deployment.sh     # End-to-end health checks
│   ├── .env.production.template # Production env var template
│   ├── nginx/
│   │   └── botforge.conf        # Nginx reverse proxy config
│   ├── systemd/
│   │   ├── botforge-api.service     # FastAPI (2 workers, 400MB max)
│   │   ├── botforge-worker.service  # ARQ worker (350MB max)
│   │   └── botforge-frontend.service # Next.js (200MB max)
│   └── redis/
│       └── redis-production.conf    # Redis (64MB max, localhost only)
├── k6/                          # Load testing scripts
│   ├── load_test.js
│   ├── http_load_test.js
│   └── README.md
└── .gitkeep
```

## Architecture

- **EC2 t3.micro** (1 vCPU, 1GB RAM + 1GB swap): Nginx, FastAPI, Next.js, ARQ worker, Redis
- **RDS db.t3.micro**: PostgreSQL 16, 20GB storage
- **S3**: File uploads (5GB free tier)

## Local Development

For local development, use Docker Compose (see `botforge/docker-compose.test.yml` for backend testing or root `docker-compose.yml` for full stack).

## Deployment

See [aws/DEPLOYMENT.md](aws/DEPLOYMENT.md) for the full deployment guide.
