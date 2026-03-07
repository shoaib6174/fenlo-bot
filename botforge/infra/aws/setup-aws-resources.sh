#!/usr/bin/env bash
# =============================================================================
# BotForge — Create AWS Free Tier Resources
# Creates: VPC security groups, EC2, Elastic IP, RDS, S3, IAM role
# Cost: $0/month (within AWS 12-month free tier)
# =============================================================================
set -euo pipefail

# --- Configuration ---
AWS_REGION="${AWS_REGION:-us-east-1}"
APP_NAME="botforge"
KEY_PAIR_NAME="${APP_NAME}-key"
DB_PASSWORD="${DB_PASSWORD:?Set DB_PASSWORD environment variable}"
DB_USERNAME="botforge"
DB_NAME="botforge"

echo "=== BotForge AWS Resource Setup ==="
echo "Region: ${AWS_REGION}"

# --- 1. Security Groups ---
echo ""
echo "--- Creating Security Groups ---"

VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" \
    --query 'Vpcs[0].VpcId' --output text --region "$AWS_REGION")
echo "Default VPC: ${VPC_ID}"

# Web server security group (EC2)
SG_WEB=$(aws ec2 create-security-group \
    --group-name "${APP_NAME}-web" \
    --description "BotForge web server - HTTP/HTTPS/SSH" \
    --vpc-id "$VPC_ID" \
    --region "$AWS_REGION" \
    --output text --query 'GroupId' 2>/dev/null || \
    aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=${APP_NAME}-web" \
        --query 'SecurityGroups[0].GroupId' --output text --region "$AWS_REGION")
echo "Web SG: ${SG_WEB}"

# Add inbound rules for web SG
for PORT in 22 80 443; do
    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_WEB" \
        --protocol tcp --port "$PORT" --cidr 0.0.0.0/0 \
        --region "$AWS_REGION" 2>/dev/null || true
done

# RDS security group (only accessible from web SG)
SG_RDS=$(aws ec2 create-security-group \
    --group-name "${APP_NAME}-rds" \
    --description "BotForge RDS - PostgreSQL from web only" \
    --vpc-id "$VPC_ID" \
    --region "$AWS_REGION" \
    --output text --query 'GroupId' 2>/dev/null || \
    aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=${APP_NAME}-rds" \
        --query 'SecurityGroups[0].GroupId' --output text --region "$AWS_REGION")
echo "RDS SG: ${SG_RDS}"

aws ec2 authorize-security-group-ingress \
    --group-id "$SG_RDS" \
    --protocol tcp --port 5432 --source-group "$SG_WEB" \
    --region "$AWS_REGION" 2>/dev/null || true

# --- 2. EC2 Key Pair ---
echo ""
echo "--- Creating EC2 Key Pair ---"
if ! aws ec2 describe-key-pairs --key-names "$KEY_PAIR_NAME" --region "$AWS_REGION" &>/dev/null; then
    aws ec2 create-key-pair \
        --key-name "$KEY_PAIR_NAME" \
        --query 'KeyMaterial' --output text \
        --region "$AWS_REGION" > "${KEY_PAIR_NAME}.pem"
    chmod 400 "${KEY_PAIR_NAME}.pem"
    echo "Key pair saved to ${KEY_PAIR_NAME}.pem"
else
    echo "Key pair '${KEY_PAIR_NAME}' already exists"
fi

# --- 3. IAM Role for EC2 -> S3 access ---
echo ""
echo "--- Creating IAM Role ---"

TRUST_POLICY='{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ec2.amazonaws.com"},
        "Action": "sts:AssumeRole"
    }]
}'

aws iam create-role \
    --role-name "${APP_NAME}-ec2-role" \
    --assume-role-policy-document "$TRUST_POLICY" 2>/dev/null || true

S3_POLICY='{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:HeadObject", "s3:ListBucket"],
        "Resource": [
            "arn:aws:s3:::'"${APP_NAME}"'-uploads",
            "arn:aws:s3:::'"${APP_NAME}"'-uploads/*"
        ]
    }]
}'

aws iam put-role-policy \
    --role-name "${APP_NAME}-ec2-role" \
    --policy-name "${APP_NAME}-s3-access" \
    --policy-document "$S3_POLICY" 2>/dev/null || true

aws iam create-instance-profile \
    --instance-profile-name "${APP_NAME}-ec2-profile" 2>/dev/null || true

aws iam add-role-to-instance-profile \
    --instance-profile-name "${APP_NAME}-ec2-profile" \
    --role-name "${APP_NAME}-ec2-role" 2>/dev/null || true

echo "IAM role created: ${APP_NAME}-ec2-role"

# Wait for instance profile to propagate
sleep 10

# --- 4. EC2 Instance (t3.micro, Ubuntu 22.04, 20GB gp3) ---
echo ""
echo "--- Launching EC2 Instance ---"

# Get latest Ubuntu 22.04 AMI
AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
              "Name=state,Values=available" \
    --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
    --output text --region "$AWS_REGION")
echo "AMI: ${AMI_ID}"

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type t3.micro \
    --key-name "$KEY_PAIR_NAME" \
    --security-group-ids "$SG_WEB" \
    --iam-instance-profile Name="${APP_NAME}-ec2-profile" \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20,"VolumeType":"gp3","Encrypted":true}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${APP_NAME}-server}]" \
    --region "$AWS_REGION" \
    --query 'Instances[0].InstanceId' --output text)
echo "Instance: ${INSTANCE_ID}"

echo "Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$AWS_REGION"

# --- 5. Elastic IP ---
echo ""
echo "--- Allocating Elastic IP ---"

ALLOC_ID=$(aws ec2 allocate-address --domain vpc --region "$AWS_REGION" \
    --query 'AllocationId' --output text)

aws ec2 associate-address \
    --instance-id "$INSTANCE_ID" \
    --allocation-id "$ALLOC_ID" \
    --region "$AWS_REGION" > /dev/null

ELASTIC_IP=$(aws ec2 describe-addresses \
    --allocation-ids "$ALLOC_ID" \
    --query 'Addresses[0].PublicIp' --output text --region "$AWS_REGION")
echo "Elastic IP: ${ELASTIC_IP}"

# --- 6. RDS Instance (db.t3.micro, PostgreSQL 16, 20GB) ---
echo ""
echo "--- Creating RDS Instance ---"

# Get default VPC subnet group
SUBNET_IDS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=${VPC_ID}" \
    --query 'Subnets[*].SubnetId' --output text --region "$AWS_REGION")

aws rds create-db-subnet-group \
    --db-subnet-group-name "${APP_NAME}-subnet" \
    --db-subnet-group-description "BotForge RDS subnets" \
    --subnet-ids $SUBNET_IDS \
    --region "$AWS_REGION" 2>/dev/null || true

aws rds create-db-instance \
    --db-instance-identifier "${APP_NAME}-db" \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version "16" \
    --master-username "$DB_USERNAME" \
    --master-user-password "$DB_PASSWORD" \
    --allocated-storage 20 \
    --storage-type gp3 \
    --storage-encrypted \
    --vpc-security-group-ids "$SG_RDS" \
    --db-subnet-group-name "${APP_NAME}-subnet" \
    --db-name "$DB_NAME" \
    --no-publicly-accessible \
    --backup-retention-period 7 \
    --region "$AWS_REGION" \
    --no-multi-az

echo "RDS instance creating (takes ~5-10 min)..."
echo "Check status: aws rds describe-db-instances --db-instance-identifier ${APP_NAME}-db --query 'DBInstances[0].DBInstanceStatus' --region ${AWS_REGION}"
echo ""
echo "To update backup retention on an existing RDS instance:"
echo "  aws rds modify-db-instance --db-instance-identifier ${APP_NAME}-db --backup-retention-period 7 --region ${AWS_REGION}"
echo "Verify:"
echo "  aws rds describe-db-instances --db-instance-identifier ${APP_NAME}-db --query 'DBInstances[0].BackupRetentionPeriod' --region ${AWS_REGION}"

# --- 7. S3 Bucket ---
echo ""
echo "--- Creating S3 Bucket ---"

if [ "$AWS_REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "${APP_NAME}-uploads" --region "$AWS_REGION" 2>/dev/null || true
else
    aws s3api create-bucket --bucket "${APP_NAME}-uploads" --region "$AWS_REGION" \
        --create-bucket-configuration LocationConstraint="$AWS_REGION" 2>/dev/null || true
fi

# Block all public access
aws s3api put-public-access-block \
    --bucket "${APP_NAME}-uploads" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Enable server-side encryption
aws s3api put-bucket-encryption \
    --bucket "${APP_NAME}-uploads" \
    --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

echo "S3 bucket created: ${APP_NAME}-uploads"

# --- Summary ---
echo ""
echo "========================================="
echo "  BotForge AWS Resources Created"
echo "========================================="
echo "EC2 Instance:  ${INSTANCE_ID}"
echo "Elastic IP:    ${ELASTIC_IP}"
echo "RDS Instance:  ${APP_NAME}-db (creating...)"
echo "S3 Bucket:     ${APP_NAME}-uploads"
echo "Key Pair:      ${KEY_PAIR_NAME}.pem"
echo ""
echo "Next steps:"
echo "  1. Point your domain A record to: ${ELASTIC_IP}"
echo "  2. Wait for RDS to be available (~5-10 min)"
echo "  3. Get RDS endpoint: aws rds describe-db-instances --db-instance-identifier ${APP_NAME}-db --query 'DBInstances[0].Endpoint.Address' --output text --region ${AWS_REGION}"
echo "  4. SSH to server: ssh -i ${KEY_PAIR_NAME}.pem ubuntu@${ELASTIC_IP}"
echo "  5. Run setup-server.sh on the EC2 instance"
echo "========================================="
