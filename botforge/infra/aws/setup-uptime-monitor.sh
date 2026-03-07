#!/bin/bash
set -e

# BotForge External Uptime Monitoring Setup
# Uses Route 53 health check ($0.50/month) OR free UptimeRobot
#
# Option A: Route 53 Health Check (AWS-integrated, costs $0.50/mo)
# Option B: UptimeRobot (free tier, 50 monitors, 5-min intervals)
#
# This script implements Option A. For Option B, see instructions below.

echo "📡 Setting up External Uptime Monitoring..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
DOMAIN="${DOMAIN:-bot.fenloai.com}"
SNS_EMAIL="${SNS_EMAIL:-your@email.com}"
MONITOR_OPTION="${MONITOR_OPTION:-uptimerobot}"  # "route53" or "uptimerobot"

if [ "$MONITOR_OPTION" = "route53" ]; then
    echo -e "${YELLOW}Using Route 53 Health Check (\$0.50/month)${NC}"

    # Get or create SNS topic
    SNS_TOPIC_ARN=$(aws sns list-topics --region "$AWS_REGION" --output text \
        --query "Topics[?contains(TopicArn, 'botforge-alerts')].TopicArn | [0]" 2>/dev/null)

    if [ -z "$SNS_TOPIC_ARN" ] || [ "$SNS_TOPIC_ARN" = "None" ]; then
        SNS_TOPIC_ARN=$(aws sns create-topic \
            --name botforge-alerts \
            --region "$AWS_REGION" \
            --output text --query 'TopicArn')
        echo "✅ Created SNS Topic: $SNS_TOPIC_ARN"
    fi

    # Create Route 53 health check
    echo "🏥 Creating Route 53 health check on https://${DOMAIN}/api/health/live..."
    HEALTH_CHECK_ID=$(aws route53 create-health-check \
        --caller-reference "botforge-health-$(date +%s)" \
        --health-check-config '{
            "FullyQualifiedDomainName": "'"$DOMAIN"'",
            "Port": 443,
            "Type": "HTTPS",
            "ResourcePath": "/api/health/live",
            "RequestInterval": 30,
            "FailureThreshold": 3,
            "EnableSNI": true
        }' \
        --output text --query 'HealthCheck.Id')

    echo "✅ Health Check ID: $HEALTH_CHECK_ID"

    # Tag the health check
    aws route53 change-tags-for-resource \
        --resource-type healthcheck \
        --resource-id "$HEALTH_CHECK_ID" \
        --add-tags Key=Name,Value=botforge-api-health

    # Create CloudWatch alarm for the health check
    echo "⚠️  Creating CloudWatch alarm for health check..."
    aws cloudwatch put-metric-alarm \
        --alarm-name "botforge-uptime" \
        --alarm-description "Alert when BotForge API health check fails" \
        --namespace "AWS/Route53" \
        --metric-name "HealthCheckStatus" \
        --dimensions Name=HealthCheckId,Value="$HEALTH_CHECK_ID" \
        --statistic Minimum \
        --period 60 \
        --evaluation-periods 2 \
        --threshold 1 \
        --comparison-operator LessThanThreshold \
        --alarm-actions "$SNS_TOPIC_ARN" \
        --ok-actions "$SNS_TOPIC_ARN" \
        --region us-east-1

    echo -e "${GREEN}✅ Route 53 health check configured!${NC}"
    echo "   Check: https://${DOMAIN}/api/health/live (every 30s)"
    echo "   Alert after: 3 consecutive failures (90s)"
    echo "   Cost: ~\$0.50/month"

else
    echo -e "${YELLOW}📋 UptimeRobot Setup Instructions (FREE)${NC}"
    echo ""
    echo "1. Go to https://uptimerobot.com and create a free account"
    echo "2. Click 'Add New Monitor' and configure:"
    echo "   - Monitor Type: HTTP(S)"
    echo "   - Friendly Name: BotForge API"
    echo "   - URL: https://${DOMAIN}/api/health/live"
    echo "   - Monitoring Interval: 5 minutes"
    echo ""
    echo "3. Add a second monitor:"
    echo "   - Monitor Type: HTTP(S)"
    echo "   - Friendly Name: BotForge Frontend"
    echo "   - URL: https://${DOMAIN}/"
    echo "   - Monitoring Interval: 5 minutes"
    echo ""
    echo "4. Set up alert contacts:"
    echo "   - Email: ${SNS_EMAIL}"
    echo "   - (Optional) Slack webhook, Telegram, etc."
    echo ""
    echo "5. Get a public status page URL to share with clients"
    echo ""
    echo -e "${GREEN}✅ UptimeRobot: Free, 50 monitors, 5-min intervals${NC}"
fi

echo ""
echo "📊 Monitoring endpoints to track:"
echo "   - https://${DOMAIN}/api/health/live  (liveness)"
echo "   - https://${DOMAIN}/api/health/ready (readiness - includes DB)"
echo "   - https://${DOMAIN}/                 (frontend)"
