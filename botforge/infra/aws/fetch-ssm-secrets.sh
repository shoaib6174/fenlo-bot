#!/bin/bash
# fetch-ssm-secrets.sh — Fetches secrets from AWS SSM Parameter Store
# and writes them to the backend .env file.
#
# Usage: Called by systemd ExecStartPre before starting services.
# Requires: AWS CLI v2, EC2 instance role with ssm:GetParameters

set -euo pipefail

ENV_FILE="/opt/botforge/app/botforge/backend/.env"
FRONTEND_ENV_FILE="/opt/botforge/app/frontend/.env.production"
REGION="us-east-1"

# List of secret parameter names to fetch
PARAM_NAMES=(
  "/botforge/prod/GROQ_API_KEY"
  "/botforge/prod/OPENAI_API_KEY"
  "/botforge/prod/PINECONE_API_KEY"
  "/botforge/prod/SECRET_KEY"
  "/botforge/prod/JWT_SECRET_KEY"
  "/botforge/prod/POSTGRES_PASSWORD"
  "/botforge/prod/VAPI_PRIVATE_KEY"
)

# Frontend params (non-secret, fetched separately so backend fetch still works if these are missing)
FRONTEND_PARAM_NAMES=(
  "/botforge/prod/NEXT_PUBLIC_HOMEPAGE_WIDGET_ID"  # pragma: allowlist secret
)

echo "Fetching secrets from SSM Parameter Store..."

# Fetch all parameters in one call
SSM_OUTPUT=$(aws ssm get-parameters \
  --names "${PARAM_NAMES[@]}" \
  --with-decryption \
  --region "$REGION" \
  --output json 2>&1)

if [ $? -ne 0 ]; then
  echo "ERROR: Failed to fetch SSM parameters: $SSM_OUTPUT" >&2
  exit 1
fi

# Parse JSON output to extract values
get_param() {
  local name="$1"
  echo "$SSM_OUTPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for p in data.get('Parameters', []):
    if p['Name'] == '$name':
        print(p['Value'])
        break
"
}

GROQ_API_KEY=$(get_param "/botforge/prod/GROQ_API_KEY")
OPENAI_API_KEY=$(get_param "/botforge/prod/OPENAI_API_KEY")
PINECONE_API_KEY=$(get_param "/botforge/prod/PINECONE_API_KEY")
SECRET_KEY=$(get_param "/botforge/prod/SECRET_KEY")
JWT_SECRET_KEY=$(get_param "/botforge/prod/JWT_SECRET_KEY")
POSTGRES_PASSWORD=$(get_param "/botforge/prod/POSTGRES_PASSWORD")
VAPI_PRIVATE_KEY=$(get_param "/botforge/prod/VAPI_PRIVATE_KEY")

# Validate all secrets were fetched
for var_name in GROQ_API_KEY OPENAI_API_KEY PINECONE_API_KEY SECRET_KEY JWT_SECRET_KEY POSTGRES_PASSWORD VAPI_PRIVATE_KEY; do
  if [ -z "${!var_name}" ]; then
    echo "ERROR: Failed to fetch $var_name from SSM" >&2
    exit 1
  fi
done

# Write clean .env file
cat > "$ENV_FILE" << ENVEOF
# Database
DATABASE_URL=postgresql+asyncpg://botforge:${POSTGRES_PASSWORD}@botforge-db.cqx04mgog0qq.us-east-1.rds.amazonaws.com:5432/botforge?ssl=require
POSTGRES_SERVER=botforge-db.cqx04mgog0qq.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_USER=botforge
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=botforge

# Redis
REDIS_URL=redis://localhost:6379/0

# Security (from SSM)
SECRET_KEY=${SECRET_KEY}
JWT_SECRET=${JWT_SECRET_KEY}

# API Keys (from SSM)
GROQ_API_KEY=${GROQ_API_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}
PINECONE_API_KEY=${PINECONE_API_KEY}
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=botforge-rag

# S3 Storage
FILE_STORAGE_BACKEND=s3
AWS_REGION=us-east-1
S3_BUCKET_NAME=botforge-uploads
S3_USE_INSTANCE_ROLE=true

# Application
ENVIRONMENT=production
DEBUG=false
FRONTEND_URL=https://bot.fenloai.com
BACKEND_URL=https://bot.fenloai.com
CORS_ORIGINS=https://bot.fenloai.com,https://rag.fenloai.com
JWT_COOKIE_DOMAIN=.fenloai.com

# Voice (Vapi)
VAPI_PRIVATE_KEY=${VAPI_PRIVATE_KEY}

# Sentry
SENTRY_ENABLED=true
SENTRY_ENVIRONMENT=production
ENVEOF

chmod 600 "$ENV_FILE"
echo "Secrets written to $ENV_FILE ($(wc -l < "$ENV_FILE") lines)"

# --- Frontend .env.production (NEXT_PUBLIC_ vars baked at build time) ---

# Fetch frontend params (non-fatal if missing — these aren't secrets)
FRONTEND_SSM_OUTPUT=$(aws ssm get-parameters \
  --names "${FRONTEND_PARAM_NAMES[@]}" \
  --region "$REGION" \
  --output json 2>&1) || true

HOMEPAGE_WIDGET_ID=$(echo "$FRONTEND_SSM_OUTPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for p in data.get('Parameters', []):
    if p['Name'] == '/botforge/prod/NEXT_PUBLIC_HOMEPAGE_WIDGET_ID':  # pragma: allowlist secret
        print(p['Value'])
        break
" 2>/dev/null || echo "")

cat > "$FRONTEND_ENV_FILE" << FEEOF
NEXT_PUBLIC_API_URL=https://bot.fenloai.com
FEEOF

# Append optional frontend vars if present
if [ -n "$HOMEPAGE_WIDGET_ID" ]; then
  echo "NEXT_PUBLIC_HOMEPAGE_WIDGET_ID=${HOMEPAGE_WIDGET_ID}" >> "$FRONTEND_ENV_FILE"
fi

chmod 644 "$FRONTEND_ENV_FILE"
echo "Frontend env written to $FRONTEND_ENV_FILE ($(wc -l < "$FRONTEND_ENV_FILE") lines)"
