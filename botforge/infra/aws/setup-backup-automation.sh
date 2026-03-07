#!/bin/bash
set -e

# BotForge Automated Backup Setup
# This script sets up automated daily backups for RDS and S3

echo "💾 Setting up Automated Backup System..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
RDS_INSTANCE="${RDS_INSTANCE:-botforge-db}"
S3_BUCKET="${S3_BUCKET:-botforge-uploads}"
BACKUP_BUCKET="${BACKUP_BUCKET:-botforge-backups}"
SNS_EMAIL="${SNS_EMAIL:-your@email.com}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

echo -e "${YELLOW}🌍 Region: ${AWS_REGION}${NC}"
echo -e "${YELLOW}🗄️  RDS Instance: ${RDS_INSTANCE}${NC}"
echo -e "${YELLOW}📦 Backup Bucket: ${BACKUP_BUCKET}${NC}"
echo -e "${YELLOW}📧 Alert Email: ${SNS_EMAIL}${NC}"
echo -e "${YELLOW}🗓️  Retention: ${BACKUP_RETENTION_DAYS} days${NC}"

# 1. Enable RDS Automated Backups
echo "🗄️  Configuring RDS automated backups..."
aws rds modify-db-instance \
  --db-instance-identifier "$RDS_INSTANCE" \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --apply-immediately \
  --region "$AWS_REGION" || echo -e "${YELLOW}⚠️  RDS backup already configured${NC}"

echo "✅ RDS automated backups enabled (7-day retention, daily at 3 AM UTC)"

# 2. Create S3 Backup Bucket
echo "📦 Creating backup bucket..."
aws s3 mb "s3://${BACKUP_BUCKET}" --region "$AWS_REGION" 2>/dev/null || \
  echo -e "${YELLOW}⚠️  Bucket already exists${NC}"

# Enable versioning on backup bucket
aws s3api put-bucket-versioning \
  --bucket "$BACKUP_BUCKET" \
  --versioning-configuration Status=Enabled \
  --region "$AWS_REGION"

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket "$BACKUP_BUCKET" \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }' \
  --region "$AWS_REGION"

# Add lifecycle policy for old backups
aws s3api put-bucket-lifecycle-configuration \
  --bucket "$BACKUP_BUCKET" \
  --lifecycle-configuration '{
    "Rules": [{
      "Id": "DeleteOldBackups",
      "Status": "Enabled",
      "Expiration": {
        "Days": '"$BACKUP_RETENTION_DAYS"'
      },
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 7
      }
    }]
  }' \
  --region "$AWS_REGION"

echo "✅ S3 backup bucket configured with versioning and lifecycle"

# 3. Create SNS Topic for Backup Alerts
echo "📬 Creating SNS topic for backup alerts..."
BACKUP_SNS_TOPIC=$(aws sns create-topic \
  --name botforge-backup-alerts \
  --region "$AWS_REGION" \
  --output text --query 'TopicArn' 2>/dev/null || \
  aws sns list-topics --region "$AWS_REGION" --output text \
  --query "Topics[?contains(TopicArn, 'botforge-backup-alerts')].TopicArn | [0]")

echo "✅ SNS Topic: $BACKUP_SNS_TOPIC"

# Subscribe email
aws sns subscribe \
  --topic-arn "$BACKUP_SNS_TOPIC" \
  --protocol email \
  --notification-endpoint "$SNS_EMAIL" \
  --region "$AWS_REGION" 2>/dev/null || true

echo -e "${GREEN}✅ Check your email to confirm backup alert subscription${NC}"

# 4. Create IAM Role for Backup Lambda
echo "🔐 Creating IAM role for backup automation..."
BACKUP_ROLE_NAME="botforge-backup-lambda-role"

TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "lambda.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF
)

aws iam create-role \
  --role-name "$BACKUP_ROLE_NAME" \
  --assume-role-policy-document "$TRUST_POLICY" \
  --region "$AWS_REGION" 2>/dev/null || \
  echo -e "${YELLOW}⚠️  IAM role already exists${NC}"

# Attach policies
aws iam attach-role-policy \
  --role-name "$BACKUP_ROLE_NAME" \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" || true

# Create custom policy for backups
BACKUP_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:CreateDBSnapshot",
        "rds:DescribeDBSnapshots",
        "rds:DeleteDBSnapshot",
        "rds:DescribeDBInstances"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::${BACKUP_BUCKET}",
        "arn:aws:s3:::${BACKUP_BUCKET}/*",
        "arn:aws:s3:::${S3_BUCKET}",
        "arn:aws:s3:::${S3_BUCKET}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "${BACKUP_SNS_TOPIC}"
    }
  ]
}
EOF
)

aws iam put-role-policy \
  --role-name "$BACKUP_ROLE_NAME" \
  --policy-name "BackupPolicy" \
  --policy-document "$BACKUP_POLICY" || true

echo "✅ IAM role configured"

# 5. Create Backup Lambda Function
echo "⚡ Creating backup Lambda function..."

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --output text --query 'Account')
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${BACKUP_ROLE_NAME}"

# Lambda function code
mkdir -p /tmp/botforge-backup-lambda
cat > /tmp/botforge-backup-lambda/lambda_function.py <<'LAMBDA_CODE'
import boto3
import os
from datetime import datetime, timedelta

rds = boto3.client('rds')
s3 = boto3.client('s3')
sns = boto3.client('sns')

RDS_INSTANCE = os.environ['RDS_INSTANCE']
S3_BUCKET = os.environ['S3_BUCKET']
BACKUP_BUCKET = os.environ['BACKUP_BUCKET']
SNS_TOPIC = os.environ['SNS_TOPIC']
RETENTION_DAYS = int(os.environ.get('RETENTION_DAYS', '30'))

def lambda_handler(event, context):
    """Automated backup handler for BotForge"""
    results = []
    errors = []

    # 1. Create RDS snapshot
    try:
        snapshot_id = f"botforge-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        print(f"Creating RDS snapshot: {snapshot_id}")

        rds.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceIdentifier=RDS_INSTANCE
        )
        results.append(f"✅ RDS snapshot created: {snapshot_id}")

        # Clean up old snapshots
        cleanup_old_snapshots()

    except Exception as e:
        error_msg = f"❌ RDS snapshot failed: {str(e)}"
        print(error_msg)
        errors.append(error_msg)

    # 2. Backup S3 uploads to backup bucket
    try:
        print(f"Backing up S3 bucket: {S3_BUCKET} → {BACKUP_BUCKET}")

        # List all objects in source bucket
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET)

        file_count = 0
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    # Copy to backup bucket with timestamp prefix
                    backup_key = f"daily/{datetime.now().strftime('%Y-%m-%d')}/{obj['Key']}"
                    s3.copy_object(
                        CopySource={'Bucket': S3_BUCKET, 'Key': obj['Key']},
                        Bucket=BACKUP_BUCKET,
                        Key=backup_key
                    )
                    file_count += 1

        results.append(f"✅ S3 backup completed: {file_count} files copied")

    except Exception as e:
        error_msg = f"❌ S3 backup failed: {str(e)}"
        print(error_msg)
        errors.append(error_msg)

    # 3. Send notification
    status = "✅ SUCCESS" if not errors else "⚠️ PARTIAL SUCCESS" if results else "❌ FAILED"
    subject = f"BotForge Backup {status}"

    message_parts = [
        f"Backup completed at: {datetime.now().isoformat()}",
        "",
        "Results:",
        *results,
        "",
        "Errors:" if errors else "No errors",
        *errors
    ]

    message = "\n".join(message_parts)

    try:
        sns.publish(
            TopicArn=SNS_TOPIC,
            Subject=subject,
            Message=message
        )
    except Exception as e:
        print(f"Failed to send SNS notification: {str(e)}")

    return {
        'statusCode': 200 if not errors else 500,
        'body': message
    }

def cleanup_old_snapshots():
    """Delete RDS snapshots older than retention period"""
    try:
        cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)

        snapshots = rds.describe_db_snapshots(
            DBInstanceIdentifier=RDS_INSTANCE,
            SnapshotType='manual'
        )['DBSnapshots']

        for snapshot in snapshots:
            if snapshot['SnapshotCreateTime'].replace(tzinfo=None) < cutoff_date:
                print(f"Deleting old snapshot: {snapshot['DBSnapshotIdentifier']}")
                rds.delete_db_snapshot(
                    DBSnapshotIdentifier=snapshot['DBSnapshotIdentifier']
                )
    except Exception as e:
        print(f"Snapshot cleanup warning: {str(e)}")
LAMBDA_CODE

# Create deployment package
cd /tmp/botforge-backup-lambda
zip -q lambda.zip lambda_function.py

# Create Lambda function
aws lambda create-function \
  --function-name botforge-backup \
  --runtime python3.12 \
  --role "$ROLE_ARN" \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda.zip \
  --timeout 300 \
  --memory-size 256 \
  --environment "Variables={
    RDS_INSTANCE=${RDS_INSTANCE},
    S3_BUCKET=${S3_BUCKET},
    BACKUP_BUCKET=${BACKUP_BUCKET},
    SNS_TOPIC=${BACKUP_SNS_TOPIC},
    RETENTION_DAYS=${BACKUP_RETENTION_DAYS}
  }" \
  --region "$AWS_REGION" 2>/dev/null || \
  aws lambda update-function-code \
    --function-name botforge-backup \
    --zip-file fileb://lambda.zip \
    --region "$AWS_REGION"

echo "✅ Lambda function created/updated"

# Clean up
rm -rf /tmp/botforge-backup-lambda

# 6. Create EventBridge Rule for Daily Backup
echo "⏰ Creating daily backup schedule..."

# Create EventBridge rule (daily at 3 AM UTC)
aws events put-rule \
  --name botforge-daily-backup \
  --schedule-expression "cron(0 3 * * ? *)" \
  --state ENABLED \
  --description "Daily backup for BotForge at 3 AM UTC" \
  --region "$AWS_REGION"

# Add Lambda permission for EventBridge
aws lambda add-permission \
  --function-name botforge-backup \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn "arn:aws:events:${AWS_REGION}:${ACCOUNT_ID}:rule/botforge-daily-backup" \
  --region "$AWS_REGION" 2>/dev/null || true

# Add Lambda as target
LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:botforge-backup"
aws events put-targets \
  --rule botforge-daily-backup \
  --targets "Id"="1","Arn"="${LAMBDA_ARN}" \
  --region "$AWS_REGION"

echo "✅ Daily backup scheduled for 3 AM UTC"

# 7. Create Manual Backup Script for EC2
echo "📝 Creating manual backup script for EC2..."

cat > /tmp/backup-now.sh <<'BACKUP_SCRIPT'
#!/bin/bash
# Manual backup trigger script
# Run this on EC2 to trigger immediate backup

echo "🚀 Triggering manual backup..."

FUNCTION_NAME="botforge-backup"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Invoke Lambda function
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --output json \
  /tmp/backup-response.json

# Show result
echo ""
echo "Response:"
cat /tmp/backup-response.json
echo ""
rm -f /tmp/backup-response.json

echo "✅ Backup triggered. Check your email for results."
BACKUP_SCRIPT

echo ""
echo -e "${YELLOW}📝 To install manual backup trigger on EC2:${NC}"
echo ""
echo "SSH into your EC2 instance and run:"
echo ""
echo "# Copy the backup trigger script"
echo "cat > /home/ubuntu/backup-now.sh <<'EOF'"
cat /tmp/backup-now.sh
echo "EOF"
echo ""
echo "chmod +x /home/ubuntu/backup-now.sh"
echo ""
echo "# Run manual backup:"
echo "./backup-now.sh"
echo ""

# Clean up
rm -f /tmp/backup-now.sh

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Automated Backup Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Configuration:"
echo "  🗄️  RDS Automated Backups: 7-day retention"
echo "  📦 S3 Backup Bucket: s3://${BACKUP_BUCKET}"
echo "  ⏰ Schedule: Daily at 3:00 AM UTC"
echo "  🗓️  Retention: ${BACKUP_RETENTION_DAYS} days"
echo "  📧 Alerts: ${SNS_EMAIL}"
echo ""
echo "Resources created:"
echo "  • RDS automated backups enabled"
echo "  • S3 backup bucket with lifecycle policy"
echo "  • Lambda function: botforge-backup"
echo "  • EventBridge rule: botforge-daily-backup"
echo "  • SNS topic: ${BACKUP_SNS_TOPIC}"
echo ""
echo "Next steps:"
echo "  1. Confirm email subscription (check inbox)"
echo "  2. Test backup: aws lambda invoke --function-name botforge-backup /tmp/test.json"
echo "  3. Monitor: https://console.aws.amazon.com/lambda/home?region=${AWS_REGION}#/functions/botforge-backup"
echo ""
echo -e "${GREEN}Backups will run automatically every day at 3 AM UTC!${NC}"
echo ""
