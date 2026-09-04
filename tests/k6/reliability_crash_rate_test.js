import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// QR-05: System recovers from third-party OSINT API failure and compiles a
// partial report; <1% crash rate. A "crash" here means the scan never reaches
// a terminal status completed partial failed 
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3001';
const TARGET_DOMAIN = __ENV.TARGET_DOMAIN || 'example.com';

const crashRate = new Rate('scan_crash_rate');

export const options = {
  scenarios: {
    crash_rate_check: {
      executor: 'per-vu-iterations',
      vus: 1,
      iterations: 10, 
      maxDuration: '5m',
    },
  },
  thresholds: {
    scan_crash_rate: ['rate<0.01'], // QR-05 target: <1% crash rate
  },
};

export default function () {
  const startedAt = Date.now();

  // 1. Trigger the scan
  const triggerRes = http.post(
    `${BASE_URL}/api/v1/scans/`,
    JSON.stringify({ domain: TARGET_DOMAIN, scan_type: 'passive_ctem' }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  const triggered = check(triggerRes, {
    'scan triggered (202)': (r) => r.status === 202,
  });

  if (!triggered) {
    crashRate.add(1); // trigger itself errored/crashed
    console.error(`Trigger failed: ${triggerRes.status} ${triggerRes.body}`);
    return;
  }

  const scanId = triggerRes.json('scan_id');

  // 2. Poll status until it reaches a terminal state, or time out
  const maxWaitMs = 90 * 1000;
  let finalStatus = null;
  let sawServerError = false;

  while (Date.now() - startedAt < maxWaitMs) {
    sleep(2); // poll every 2s

    const statusRes = http.get(`${BASE_URL}/api/v1/scans/${scanId}/status`);

    if (statusRes.status >= 500) {
      sawServerError = true;
      break;
    }

    const status = statusRes.json('status');

    if (status === 'completed' || status === 'failed' || status === 'partial') {
      finalStatus = status;
      break;
    }
  }

  // "Crashed" = trigger errored, the status endpoint
  // Reaching "failed" or "partial" is NOT a crash - it's the expected
  const crashed = sawServerError || finalStatus === null;
  crashRate.add(crashed ? 1 : 0);

  check(finalStatus, {
    'scan reached a terminal status (no crash)': () => !crashed,
  });

  const elapsedMs = Date.now() - startedAt;
  console.log(`Scan ${scanId}: ${crashed ? 'CRASHED' : finalStatus} in ${elapsedMs}ms`);
}