// BotForge — k6 Load Test
// Validates NFR-01 (first token <1s) and NFR-03 (50 concurrent connections)
//
// Usage:
//   k6 run infra/k6/load_test.js
//
// Environment variables:
//   BASE_URL=https://botforge.fenloai.com
//   WS_TOKEN=<short-lived-ws-token>
//   WORKSPACE_ID=<demo-workspace-id>

import ws from 'k6/ws';
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

// Custom metrics
const firstTokenLatency = new Trend('first_token_latency', true);
const messageCount = new Counter('messages_sent');
const tokensReceived = new Counter('tokens_received');

// Load test configuration
export const options = {
  stages: [
    { duration: '30s', target: 5 },    // Warm up: ramp to 5 users
    { duration: '1m', target: 10 },    // Ramp to 10 concurrent
    { duration: '2m', target: 25 },    // Ramp to 25 concurrent
    { duration: '2m', target: 50 },    // NFR-03: Test 50 concurrent connections
    { duration: '1m', target: 50 },    // Hold at 50
    { duration: '1m', target: 0 },     // Ramp down
  ],
  thresholds: {
    // NFR-01: First token latency < 1s at P95
    'first_token_latency': ['p95<1000', 'p99<2000'],

    // NFR-03: Response initiation < 2s at P99
    'http_req_duration': ['p99<2000'],

    // WebSocket connection establishment
    'ws_connecting': ['p95<1000'],

    // Overall success rate
    'checks': ['rate>0.95'],  // 95% of checks should pass
  },
};

// Test questions (simulating real user queries)
const questions = [
  "What services do you offer?",
  "What are your pricing plans?",
  "How do I get started?",
  "Do you offer customer support?",
  "What are your business hours?",
  "Can I schedule a demo?",
  "What's your refund policy?",
  "How long does onboarding take?",
];

export default function () {
  const baseUrl = __ENV.BASE_URL || 'http://localhost:8000';
  const wsToken = __ENV.WS_TOKEN || 'test-token';
  const workspaceId = __ENV.WORKSPACE_ID || 'demo-workspace';

  // Pick random question
  const question = questions[Math.floor(Math.random() * questions.length)];

  // WebSocket streaming test
  const wsUrl = `${baseUrl.replace('http', 'ws')}/api/v1/chat/stream?token=${wsToken}`;

  const startTime = Date.now();
  let firstTokenTime = null;
  let tokenCount = 0;
  let messageComplete = false;

  const res = ws.connect(wsUrl, {}, function (socket) {
    socket.on('open', () => {
      // Send chat message
      socket.send(JSON.stringify({
        message: question,
        workspace_id: workspaceId,
        conversation_id: null,  // New conversation
      }));
      messageCount.add(1);
    });

    socket.on('message', (data) => {
      try {
        const msg = JSON.parse(data);

        if (msg.type === 'token') {
          // Record first token latency (NFR-01)
          if (!firstTokenTime) {
            firstTokenTime = Date.now();
            const latency = firstTokenTime - startTime;
            firstTokenLatency.add(latency);
          }
          tokenCount++;
          tokensReceived.add(1);
        }

        if (msg.type === 'done') {
          messageComplete = true;
          socket.close();
        }

        if (msg.type === 'error') {
          console.error('WebSocket error:', msg.message);
          socket.close();
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    });

    socket.on('error', (e) => {
      console.error('WebSocket error:', e);
    });

    // Timeout after 30 seconds
    socket.setTimeout(() => {
      console.warn('WebSocket timeout - closing');
      socket.close();
    }, 30000);
  });

  // Validate WebSocket response
  check(res, {
    'WebSocket connected': (r) => r && r.status === 101,
    'Received first token': () => firstTokenTime !== null,
    'Received at least 10 tokens': () => tokenCount >= 10,
    'Message completed': () => messageComplete,
  });

  // Small delay between iterations
  sleep(Math.random() * 2 + 1);  // 1-3 seconds
}

// HTTP fallback test (for non-streaming endpoints)
export function httpTest() {
  const baseUrl = __ENV.BASE_URL || 'http://localhost:8000';

  // Test health endpoint (should be fast)
  const healthRes = http.get(`${baseUrl}/api/health/live`);
  check(healthRes, {
    'Health check status 200': (r) => r.status === 200,
    'Health check < 100ms': (r) => r.timings.duration < 100,
  });

  sleep(1);
}

// Summary handler
export function handleSummary(data) {
  return {
    'summary.json': JSON.stringify(data),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;

  let summary = `\n${indent}✓ Load Test Summary\n`;
  summary += `${indent}${'='.repeat(50)}\n\n`;

  // Overall metrics
  const metrics = data.metrics;

  summary += `${indent}📊 Key Metrics:\n`;
  summary += `${indent}  • Messages sent: ${metrics.messages_sent?.values.count || 0}\n`;
  summary += `${indent}  • Tokens received: ${metrics.tokens_received?.values.count || 0}\n`;
  summary += `${indent}  • First token latency (P95): ${(metrics.first_token_latency?.values['p(95)'] || 0).toFixed(0)}ms\n`;
  summary += `${indent}  • First token latency (P99): ${(metrics.first_token_latency?.values['p(99)'] || 0).toFixed(0)}ms\n`;
  summary += `${indent}  • HTTP req duration (P99): ${(metrics.http_req_duration?.values['p(99)'] || 0).toFixed(0)}ms\n`;
  summary += `${indent}  • WS connecting (P95): ${(metrics.ws_connecting?.values['p(95)'] || 0).toFixed(0)}ms\n`;
  summary += `${indent}  • Check success rate: ${((metrics.checks?.values.rate || 0) * 100).toFixed(1)}%\n\n`;

  // Threshold results
  summary += `${indent}🎯 Threshold Results:\n`;
  const thresholds = data.root_group.checks || [];
  for (const check of thresholds) {
    const status = check.passes === check.fails + check.passes ? '✓' : '✗';
    summary += `${indent}  ${status} ${check.name}: ${check.passes}/${check.fails + check.passes}\n`;
  }

  summary += `\n${indent}${'='.repeat(50)}\n`;

  // NFR validation
  const firstTokenP95 = metrics.first_token_latency?.values['p(95)'] || 0;
  const httpReqP99 = metrics.http_req_duration?.values['p(99)'] || 0;

  summary += `\n${indent}📋 NFR Validation:\n`;
  summary += `${indent}  • NFR-01 (First token <1s @ P95): ${firstTokenP95 < 1000 ? '✓ PASS' : '✗ FAIL'} (${firstTokenP95.toFixed(0)}ms)\n`;
  summary += `${indent}  • NFR-03 (Response <2s @ P99): ${httpReqP99 < 2000 ? '✓ PASS' : '✗ FAIL'} (${httpReqP99.toFixed(0)}ms)\n`;

  return summary;
}
