#!/usr/bin/env bash
# =============================================================================
# BotForge — End-to-End Deployment Verification
# Run this after deploy.sh and setup-ssl.sh
# =============================================================================
set -euo pipefail

DOMAIN="${DOMAIN:-localhost}"
SCHEME="https"
if [ "$DOMAIN" = "localhost" ]; then
    SCHEME="http"
fi
BASE_URL="${SCHEME}://${DOMAIN}"

PASS=0
FAIL=0

check() {
    local name="$1"
    local result="$2"
    if [ "$result" = "ok" ]; then
        echo "  [PASS] ${name}"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] ${name} (got: ${result})"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== BotForge Deployment Verification ==="
echo "Target: ${BASE_URL}"
echo ""

# --- 1. Systemd Services ---
echo "--- Systemd Services ---"
for svc in botforge-api botforge-worker botforge-frontend redis-server nginx; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || echo "inactive")
    check "${svc}" "$([ "$STATUS" = "active" ] && echo "ok" || echo "$STATUS")"
done

# --- 2. Health Endpoints ---
echo ""
echo "--- Health Endpoints ---"

API_HEALTH=$(curl -sf "${BASE_URL}/health" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null || echo "unreachable")
check "GET /health" "$([ "$API_HEALTH" = "ok" ] && echo "ok" || echo "$API_HEALTH")"

API_LIVE=$(curl -sf "${BASE_URL}/api/health/live" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null || echo "unreachable")
check "GET /api/health/live" "$([ "$API_LIVE" = "ok" ] && echo "ok" || echo "$API_LIVE")"

# --- 3. SSL Certificate ---
echo ""
echo "--- SSL ---"
if [ "$SCHEME" = "https" ]; then
    SSL_STATUS=$(curl -sI "${BASE_URL}" 2>/dev/null | head -1 | grep -c "200\|301\|302" || echo "0")
    check "SSL/HTTPS working" "$([ "$SSL_STATUS" -gt 0 ] && echo "ok" || echo "failed")"
else
    echo "  [SKIP] SSL (localhost mode)"
fi

# --- 4. Frontend ---
echo ""
echo "--- Frontend ---"
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/" 2>/dev/null || echo "000")
check "Frontend loads (HTTP ${FRONTEND_STATUS})" "$([ "$FRONTEND_STATUS" = "200" ] && echo "ok" || echo "http_${FRONTEND_STATUS}")"

# --- 5. Demo Mode ---
echo ""
echo "--- Demo Mode ---"
DEMO_STATUS=$(curl -sf -X POST "${BASE_URL}/api/v1/auth/demo" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('ok' if d.get('access_token') else 'no_token')" 2>/dev/null || echo "unreachable")
check "Demo login" "$([ "$DEMO_STATUS" = "ok" ] && echo "ok" || echo "$DEMO_STATUS")"

# --- 6. Memory Usage ---
echo ""
echo "--- Memory ---"
MEM_USED=$(free -m | awk 'NR==2{print $3}')
MEM_TOTAL=$(free -m | awk 'NR==2{print $2}')
check "Memory < 800MB used" "$([ "$MEM_USED" -lt 800 ] && echo "ok" || echo "${MEM_USED}MB/${MEM_TOTAL}MB")"

# --- Summary ---
echo ""
echo "========================================="
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "========================================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
