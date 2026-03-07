// BotForge — Simple HTTP Load Test
// Tests synchronous endpoints for baseline performance
//
// Usage:
//   k6 run infra/k6/http_load_test.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const healthCheckDuration = new Trend('health_check_duration');
const apiResponseTime = new Trend('api_response_time');

export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp to 10 users
    { duration: '1m', target: 50 },    // Ramp to 50 concurrent
    { duration: '2m', target: 100 },   // Ramp to 100 concurrent
    { duration: '1m', target: 100 },   // Hold at 100
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p95<500', 'p99<1000'],  // Health endpoints should be fast
    'api_response_time': ['p95<2000', 'p99<5000'], // API endpoints
    'errors': ['rate<0.05'],  // Error rate < 5%
    'http_req_failed': ['rate<0.05'],
  },
};

export default function () {
  const baseUrl = __ENV.BASE_URL || 'http://localhost:8000';

  // Test 1: Liveness endpoint (should be very fast)
  const liveRes = http.get(`${baseUrl}/api/health/live`);
  healthCheckDuration.add(liveRes.timings.duration);

  check(liveRes, {
    'Liveness status 200': (r) => r.status === 200,
    'Liveness < 50ms': (r) => r.timings.duration < 50,
    'Liveness has status': (r) => r.json('status') === 'ok',
  }) || errorRate.add(1);

  sleep(0.5);

  // Test 2: Readiness endpoint (DB + Redis check)
  const readyRes = http.get(`${baseUrl}/api/health/ready`);
  healthCheckDuration.add(readyRes.timings.duration);

  check(readyRes, {
    'Readiness status 200': (r) => r.status === 200,
    'Readiness < 200ms': (r) => r.timings.duration < 200,
  }) || errorRate.add(1);

  sleep(0.5);

  // Test 3: Full status endpoint
  const statusRes = http.get(`${baseUrl}/api/health/status`);
  apiResponseTime.add(statusRes.timings.duration);

  check(statusRes, {
    'Status returns 200': (r) => r.status === 200,
    'Status < 2s': (r) => r.timings.duration < 2000,
  }) || errorRate.add(1);

  sleep(1);

  // Test 4: Demo mode endpoint
  const demoRes = http.post(`${baseUrl}/api/v1/auth/demo`, null, {
    headers: { 'Content-Type': 'application/json' },
  });
  apiResponseTime.add(demoRes.timings.duration);

  check(demoRes, {
    'Demo mode works': (r) => r.status === 200,
    'Demo returns token': (r) => r.json('access_token') !== undefined,
  }) || errorRate.add(1);

  sleep(Math.random() * 2 + 1);  // 1-3 seconds between iterations
}

export function handleSummary(data) {
  const passed = Object.entries(data.metrics)
    .filter(([name, metric]) => metric.thresholds)
    .every(([name, metric]) => {
      return Object.values(metric.thresholds).every(t => t.ok);
    });

  console.log('\n' + '='.repeat(60));
  console.log('📊 HTTP Load Test Results');
  console.log('='.repeat(60));
  console.log(`Requests: ${data.metrics.http_reqs?.values.count || 0}`);
  console.log(`Failed: ${data.metrics.http_req_failed?.values.count || 0}`);
  console.log(`Error rate: ${((data.metrics.errors?.values.rate || 0) * 100).toFixed(2)}%`);
  console.log(`Avg response time: ${(data.metrics.http_req_duration?.values.avg || 0).toFixed(0)}ms`);
  console.log(`P95 response time: ${(data.metrics.http_req_duration?.values['p(95)'] || 0).toFixed(0)}ms`);
  console.log(`P99 response time: ${(data.metrics.http_req_duration?.values['p(99)'] || 0).toFixed(0)}ms`);
  console.log('='.repeat(60));
  console.log(passed ? '✅ All thresholds passed!' : '❌ Some thresholds failed!');
  console.log('='.repeat(60) + '\n');

  return {
    'http-load-test-summary.json': JSON.stringify(data, null, 2),
  };
}
