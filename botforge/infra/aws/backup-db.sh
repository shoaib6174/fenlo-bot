#!/usr/bin/env bash
# =============================================================================
# BotForge — Database Backup (pg_dump RDS to S3)
# Add to crontab: 0 3 * * * /opt/botforge/app/botforge/infra/aws/backup-db.sh
# =============================================================================
set -euo pipefail

APP_DIR="/opt/botforge/app"
BACKEND_DIR="${APP_DIR}/botforge/backend"
BACKUP_DIR="/tmp/botforge-backups"
S3_BUCKET="botforge-uploads"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="botforge_backup_${TIMESTAMP}.sql.gz"

# Load database URL from .env
if [ -f "${BACKEND_DIR}/.env" ]; then
    DATABASE_URL=$(grep ^DATABASE_URL "${BACKEND_DIR}/.env" | cut -d'=' -f2-)
fi
DATABASE_URL="${DATABASE_URL:?DATABASE_URL not found}"

# Extract connection details from URL
# Format: postgresql+asyncpg://user:pass@host:port/dbname
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\(.*\):.*|\1|p' | cut -d'/' -f1)
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo "$DATABASE_URL" | sed -n 's|.*/\(.*\)|\1|p' | cut -d'?' -f1)
DB_USER=$(echo "$DATABASE_URL" | sed -n 's|.*://\(.*\):.*@.*|\1|p')
DB_PASS=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\(.*\)@.*|\1|p')

mkdir -p "$BACKUP_DIR"

echo "=== BotForge Database Backup ==="
echo "Timestamp: ${TIMESTAMP}"

# Dump and compress
PGPASSWORD="$DB_PASS" pg_dump \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-owner --no-acl \
    | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
echo "Backup size: ${SIZE}"

# Upload to S3
aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://${S3_BUCKET}/backups/${BACKUP_FILE}"
echo "Uploaded to s3://${S3_BUCKET}/backups/${BACKUP_FILE}"

# Cleanup local backup
rm -f "${BACKUP_DIR}/${BACKUP_FILE}"

# Remove S3 backups older than 30 days
aws s3 ls "s3://${S3_BUCKET}/backups/" | while read -r line; do
    FILE_DATE=$(echo "$line" | awk '{print $1}')
    FILE_NAME=$(echo "$line" | awk '{print $4}')
    if [ -n "$FILE_NAME" ]; then
        FILE_AGE=$(( ($(date +%s) - $(date -d "$FILE_DATE" +%s 2>/dev/null || echo 0)) / 86400 ))
        if [ "$FILE_AGE" -gt 30 ]; then
            aws s3 rm "s3://${S3_BUCKET}/backups/${FILE_NAME}"
            echo "Removed old backup: ${FILE_NAME}"
        fi
    fi
done

echo "Backup complete!"
