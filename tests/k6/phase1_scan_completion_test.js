import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

// QR-02: Phase 1 CTEM scan completes within 60s for 90% of requests
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3001';
const TARGET_DOMAIN = __ENV.TARGET_DOMAIN || 'example.com';

const scanDuration = new Trend('scan_completion_time', true);

export const options = {
  scenarios: {
    scan_completion: {
      executor: 'per-vu-iterations',
      vus: 1,
      iterations: 10, // small, sequential - this hits real external OSINT providers
      maxDuration: '5m',
    },
  },
  thresholds: {
    scan_completion_time: ['p(90)<60000'], // QR-02 target: p90 < 60s
  },
};

export default function () {
  // 1. Trigger the scan
  const startedAt = Date.now();
  const triggerRes = http.post(
    `${BASE_URL}/api/v1/scans/`,
    JSON.stringify({ domain: TARGET_DOMAIN, scan_type: 'passive_ctem' }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  const triggered = check(triggerRes, {
    'scan triggered (202)': (r) => r.status === 202,
  });

  if (!triggered) {
    console.error(`Trigger failed: ${triggerRes.status} ${triggerRes.body}`);
    return;
  }

  const scanId = triggerRes.json('scan_id');

  // 2. Poll status until completed/failed or timeout
  const maxWaitMs = 90 * 1000;
  let finalStatus = null;

  while (Date.now() - startedAt < maxWaitMs) {
    sleep(2); // poll every 2s

    const statusRes = http.get(`${BASE_URL}/api/v1/scans/${scanId}/status`);
    const status = statusRes.json('status');

    if (status === 'completed' || status === 'failed' || status === 'partial') {
      finalStatus = status;
      break;
    }
  }

  const elapsedMs = Date.now() - startedAt;
  scanDuration.add(elapsedMs);

  check(finalStatus, {
    'scan completed': (s) => s === 'completed',
  });

  console.log(`Scan ${scanId}: ${finalStatus ?? 'timeout'} in ${elapsedMs}ms`);
}