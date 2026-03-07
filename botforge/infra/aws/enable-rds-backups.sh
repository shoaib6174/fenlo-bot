#!/bin/bash
# =============================================================================
# Enable RDS Automated Backups (7-day retention)
# Run this on production to update the existing RDS instance
# =============================================================================

set -e

APP_NAME="botforge"
AWS_REGION="us-east-1"

echo "=== Enabling RDS Automated Backups ==="
echo "Instance: ${APP_NAME}-db"
echo "Region: ${AWS_REGION}"
echo "Backup retention: 7 days"
echo ""

# Check current backup retention
echo "Current backup retention:"
aws rds describe-db-instances \
    --db-instance-identifier "${APP_NAME}-db" \
    --query 'DBInstances[0].BackupRetentionPeriod' \
    --output text \
    --region "${AWS_REGION}"
echo ""

# Apply the change
echo "Applying change..."
aws rds modify-db-instance \
    --db-instance-identifier "${APP_NAME}-db" \
    --backup-retention-period 7 \
    --apply-immediately \
    --region "${AWS_REGION}"

echo ""
echo "Change submitted. Waiting 10 seconds before verifying..."
sleep 10

# Verify
echo ""
echo "New backup retention:"
aws rds describe-db-instances \
    --db-instance-identifier "${APP_NAME}-db" \
    --query 'DBInstances[0].BackupRetentionPeriod' \
    --output text \
    --region "${AWS_REGION}"

echo ""
echo "✓ RDS automated backups enabled (7-day retention)"
echo ""
echo "Backup window and preferred backup time can be configured in AWS Console:"
echo "  https://console.aws.amazon.com/rds/home?region=${AWS_REGION}#database:id=${APP_NAME}-db;is-cluster=false"
