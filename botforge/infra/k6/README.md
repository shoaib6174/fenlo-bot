# BotForge — Load Testing with k6

This directory contains k6 load test scripts for validating NFRs (Non-Functional Requirements) before deployment.

## Prerequisites

Install k6:
```bash
# macOS
brew install k6

# Linux
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Windows
choco install k6
```

## Test Scripts

### 1. HTTP Load Test (`http_load_test.js`)

Tests synchronous HTTP endpoints for baseline performance.

**Run:**
```bash
k6 run infra/k6/http_load_test.js -e BASE_URL=https://botforge.fenloai.com
```

**Validates:**
- Health check latency (<50ms for liveness)
- API response times (<2s for status endpoint)
- Error rate (<5%)
- 100 concurrent users

**Thresholds:**
- `http_req_duration`: P95 <500ms, P99 <1000ms
- `api_response_time`: P95 <2000ms, P99 <5000ms
- `errors`: <5% error rate

---

### 2. WebSocket Load Test (`load_test.js`)

Tests real-time streaming chat with WebSockets. Validates NFR-01 and NFR-03.

**Setup:**
```bash
# 1. Get a demo token
curl -X POST https://botforge.fenloai.com/api/v1/auth/demo

# 2. Get WebSocket token
curl https://botforge.fenloai.com/api/v1/auth/ws-token \
  -H "Authorization: Bearer <access-token>"

# 3. Get workspace ID from demo response
# Note the workspace_id value
```

**Run:**
```bash
k6 run infra/k6/load_test.js \
  -e BASE_URL=https://botforge.fenloai.com \
  -e WS_TOKEN=<ws-token> \
  -e WORKSPACE_ID=<workspace-id>
```

**Validates:**
- **NFR-01**: First token latency <1s at P95
- **NFR-03**: 50 concurrent WebSocket connections
- Message completion rate >95%
- Average tokens per response

**Thresholds:**
- `first_token_latency`: P95 <1000ms, P99 <2000ms
- `ws_connecting`: P95 <1000ms
- `checks`: >95% success rate

---

## Test Stages

Both tests use similar load progression:

1. **Warm-up** (30s): Ramp to initial load
2. **Ramp-up** (1-2m): Gradually increase load
3. **Peak** (1-2m): Test at maximum concurrent users
4. **Hold** (1m): Sustained peak load
5. **Ramp-down** (30s-1m): Graceful decrease

## Interpreting Results

### Success Criteria

**HTTP Test:**
- ✅ All requests complete successfully
- ✅ P95 latency <500ms for health checks
- ✅ P99 latency <1s for health checks
- ✅ Error rate <5%

**WebSocket Test:**
- ✅ NFR-01: First token arrives <1s (P95)
- ✅ NFR-03: System handles 50 concurrent connections
- ✅ >95% of messages complete successfully
- ✅ No connection timeouts

### Common Issues

**High latency (>2s P95):**
- Check database connection pool settings
- Verify Redis is responding quickly
- Review backend logs for slow queries

**Connection failures:**
- Check rate limiting configuration
- Verify CORS settings
- Review WebSocket configuration

**Timeout errors:**
- LLM provider may be slow
- Check circuit breaker state
- Review worker queue length

## Running Before Deployment

**Always run these tests BEFORE claiming performance metrics in proposals:**

```bash
# 1. Deploy to staging
# 2. Run HTTP load test
k6 run infra/k6/http_load_test.js -e BASE_URL=<staging-url>

# 3. Run WebSocket load test
# (Get tokens first - see setup above)
k6 run infra/k6/load_test.js \
  -e BASE_URL=<staging-url> \
  -e WS_TOKEN=<token> \
  -e WORKSPACE_ID=<id>

# 4. Review results
# 5. Fix any failures
# 6. Deploy to production
# 7. Run tests again on production
```

## CI/CD Integration

Add to GitHub Actions (optional):

```yaml
# .github/workflows/load-test.yml
name: Load Tests
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install k6
        run: |
          curl https://github.com/grafana/k6/releases/download/v0.45.0/k6-v0.45.0-linux-amd64.tar.gz -L | tar xvz
          sudo mv k6-v0.45.0-linux-amd64/k6 /usr/local/bin/
      - name: Run HTTP load test
        run: k6 run infra/k6/http_load_test.js -e BASE_URL=${{ secrets.API_URL }}
```

## References

- [k6 Documentation](https://k6.io/docs/)
- [k6 Thresholds](https://k6.io/docs/using-k6/thresholds/)
- [k6 Metrics](https://k6.io/docs/using-k6/metrics/)
- [BotForge PRD - NFRs](../../docs/specs/PRD.md#nfrs)
