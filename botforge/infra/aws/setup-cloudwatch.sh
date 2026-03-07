#!/bin/bash
set -e

# BotForge CloudWatch Monitoring Setup
# This script sets up CloudWatch monitoring for EC2, RDS, and application logs

echo "🔍 Setting up CloudWatch Monitoring..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
INSTANCE_ID="${INSTANCE_ID:-i-0bb2afe73a14084cb}"
RDS_INSTANCE="${RDS_INSTANCE:-botforge-db}"
SNS_EMAIL="${SNS_EMAIL:-your@email.com}"

echo -e "${YELLOW}📧 Email for alerts: ${SNS_EMAIL}${NC}"
echo -e "${YELLOW}🌍 Region: ${AWS_REGION}${NC}"
echo -e "${YELLOW}🖥️  EC2 Instance: ${INSTANCE_ID}${NC}"
echo -e "${YELLOW}🗄️  RDS Instance: ${RDS_INSTANCE}${NC}"

# 1. Create SNS Topic for Alerts
echo "📬 Creating SNS topic for alerts..."
SNS_TOPIC_ARN=$(aws sns create-topic \
  --name botforge-alerts \
  --region "$AWS_REGION" \
  --output text --query 'TopicArn' 2>/dev/null || \
  aws sns list-topics --region "$AWS_REGION" --output text \
  --query "Topics[?contains(TopicArn, 'botforge-alerts')].TopicArn | [0]")

echo "✅ SNS Topic ARN: $SNS_TOPIC_ARN"

# Subscribe email to SNS topic
echo "📧 Subscribing $SNS_EMAIL to alerts..."
aws sns subscribe \
  --topic-arn "$SNS_TOPIC_ARN" \
  --protocol email \
  --notification-endpoint "$SNS_EMAIL" \
  --region "$AWS_REGION" 2>/dev/null || true

echo -e "${GREEN}✅ Check your email to confirm the subscription!${NC}"

# 2. EC2 CPU Alarm
echo "⚠️  Creating EC2 CPU alarm (>80%)..."
aws cloudwatch put-metric-alarm \
  --alarm-name botforge-ec2-cpu-high \
  --alarm-description "Alert when EC2 CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=InstanceId,Value="$INSTANCE_ID" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --region "$AWS_REGION"

echo "✅ EC2 CPU alarm created"

# 3. EC2 Status Check Alarm
echo "⚠️  Creating EC2 status check alarm..."
aws cloudwatch put-metric-alarm \
  --alarm-name botforge-ec2-status-check \
  --alarm-description "Alert when EC2 status check fails" \
  --metric-name StatusCheckFailed \
  --namespace AWS/EC2 \
  --statistic Maximum \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=InstanceId,Value="$INSTANCE_ID" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --region "$AWS_REGION"

echo "✅ EC2 status check alarm created"

# 4. RDS CPU Alarm
echo "⚠️  Creating RDS CPU alarm (>80%)..."
aws cloudwatch put-metric-alarm \
  --alarm-name botforge-rds-cpu-high \
  --alarm-description "Alert when RDS CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=DBInstanceIdentifier,Value="$RDS_INSTANCE" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --region "$AWS_REGION"

echo "✅ RDS CPU alarm created"

# 5. RDS Storage Alarm
echo "⚠️  Creating RDS storage alarm (<2GB)..."
aws cloudwatch put-metric-alarm \
  --alarm-name botforge-rds-storage-low \
  --alarm-description "Alert when RDS free storage is below 2GB" \
  --metric-name FreeStorageSpace \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 2147483648 \
  --comparison-operator LessThanThreshold \
  --dimensions Name=DBInstanceIdentifier,Value="$RDS_INSTANCE" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --region "$AWS_REGION"

echo "✅ RDS storage alarm created"

# 6. RDS Connection Alarm
echo "⚠️  Creating RDS connection alarm (>40 connections)..."
aws cloudwatch put-metric-alarm \
  --alarm-name botforge-rds-connections-high \
  --alarm-description "Alert when RDS connections exceed 40" \
  --metric-name DatabaseConnections \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 40 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=DBInstanceIdentifier,Value="$RDS_INSTANCE" \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --region "$AWS_REGION"

echo "✅ RDS connection alarm created"

# 7. Create CloudWatch Dashboard
echo "📊 Creating CloudWatch Dashboard..."
DASHBOARD_BODY=$(cat <<EOF
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "AWS/EC2", "CPUUtilization", { "stat": "Average", "dimensions": { "InstanceId": "$INSTANCE_ID" } } ]
        ],
        "period": 300,
        "stat": "Average",
        "region": "$AWS_REGION",
        "title": "EC2 CPU Utilization",
        "yAxis": { "left": { "min": 0, "max": 100 } }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "AWS/RDS", "CPUUtilization", { "stat": "Average", "dimensions": { "DBInstanceIdentifier": "$RDS_INSTANCE" } } ]
        ],
        "period": 300,
        "stat": "Average",
        "region": "$AWS_REGION",
        "title": "RDS CPU Utilization",
        "yAxis": { "left": { "min": 0, "max": 100 } }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "AWS/RDS", "DatabaseConnections", { "stat": "Sum", "dimensions": { "DBInstanceIdentifier": "$RDS_INSTANCE" } } ]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "$AWS_REGION",
        "title": "RDS Database Connections"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "AWS/RDS", "FreeStorageSpace", { "stat": "Average", "dimensions": { "DBInstanceIdentifier": "$RDS_INSTANCE" } } ]
        ],
        "period": 300,
        "stat": "Average",
        "region": "$AWS_REGION",
        "title": "RDS Free Storage (Bytes)"
      }
    }
  ]
}
EOF
)

aws cloudwatch put-dashboard \
  --dashboard-name botforge-monitoring \
  --dashboard-body "$DASHBOARD_BODY" \
  --region "$AWS_REGION"

echo "✅ CloudWatch Dashboard created"

# 8. Install CloudWatch Agent on EC2 (if SSH access available)
echo ""
echo -e "${YELLOW}📝 To complete setup, install CloudWatch Agent on EC2:${NC}"
echo ""
echo "SSH into your EC2 instance and run:"
echo ""
echo "sudo bash <<'CLOUDWATCH_AGENT'"
echo "# Download and install CloudWatch Agent"
echo "wget https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb"
echo "sudo dpkg -i amazon-cloudwatch-agent.deb"
echo ""
echo "# Create CloudWatch Agent config"
echo "sudo cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json <<EOF"
echo "{"
echo "  \"metrics\": {"
echo "    \"namespace\": \"BotForge\","
echo "    \"metrics_collected\": {"
echo "      \"mem\": {"
echo "        \"measurement\": ["
echo "          {\"name\": \"mem_used_percent\", \"unit\": \"Percent\"}"
echo "        ],"
echo "        \"metrics_collection_interval\": 60"
echo "      },"
echo "      \"disk\": {"
echo "        \"measurement\": ["
echo "          {\"name\": \"used_percent\", \"unit\": \"Percent\"}"
echo "        ],"
echo "        \"metrics_collection_interval\": 60,"
echo "        \"resources\": [\"*\"]"
echo "      }"
echo "    }"
echo "  },"
echo "  \"logs\": {"
echo "    \"logs_collected\": {"
echo "      \"files\": {"
echo "        \"collect_list\": ["
echo "          {"
echo "            \"file_path\": \"/opt/botforge/logs/api.log\","
echo "            \"log_group_name\": \"/botforge/api\","
echo "            \"log_stream_name\": \"{instance_id}\""
echo "          },"
echo "          {"
echo "            \"file_path\": \"/opt/botforge/logs/worker.log\","
echo "            \"log_group_name\": \"/botforge/worker\","
echo "            \"log_stream_name\": \"{instance_id}\""
echo "          },"
echo "          {"
echo "            \"file_path\": \"/var/log/nginx/access.log\","
echo "            \"log_group_name\": \"/botforge/nginx/access\","
echo "            \"log_stream_name\": \"{instance_id}\""
echo "          },"
echo "          {"
echo "            \"file_path\": \"/var/log/nginx/error.log\","
echo "            \"log_group_name\": \"/botforge/nginx/error\","
echo "            \"log_stream_name\": \"{instance_id}\""
echo "          }"
echo "        ]"
echo "      }"
echo "    }"
echo "  }"
echo "}"
echo "EOF"
echo ""
echo "# Start CloudWatch Agent"
echo "sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \\"
echo "  -a fetch-config \\"
echo "  -m ec2 \\"
echo "  -s \\"
echo "  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json"
echo "CLOUDWATCH_AGENT"
echo ""

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ CloudWatch Monitoring Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📊 Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=botforge-monitoring"
echo "⚠️  Alarms: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#alarmsV2:"
echo "📬 SNS Topic: $SNS_TOPIC_ARN"
echo ""
echo "Alarms configured:"
echo "  • EC2 CPU > 80%"
echo "  • EC2 Status Check Failed"
echo "  • RDS CPU > 80%"
echo "  • RDS Free Storage < 2GB"
echo "  • RDS Connections > 40"
echo ""
echo -e "${YELLOW}⚠️  Don't forget to:${NC}"
echo "  1. Confirm email subscription (check your inbox)"
echo "  2. Install CloudWatch Agent on EC2 (see instructions above)"
echo ""
