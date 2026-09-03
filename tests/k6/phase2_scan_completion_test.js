import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

// QR-13: Phase 2 active vulnerability scan completes within 5 minutes for 90% of requests
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3001';
const TARGET_DOMAIN = __ENV.TARGET_DOMAIN || 'example.com';
const VERIFIED_DOMAIN_ID = __ENV.VERIFIED_DOMAIN_ID; // required - see seed SQL
const AUTH_TOKEN = __ENV.AUTH_TOKEN; 

const scanDuration = new Trend('phase2_scan_completion_time', true);

export const options = {
  scenarios: {
    scan_completion: {
      executor: 'per-vu-iterations',
      vus: 1,
      iterations: 5, 
      maxDuration: '30m',
    },
  },
  thresholds: {
    phase2_scan_completion_time: ['p(90)<30000'], // QR-13 target: p90 < 30s
  },
};

export default function () {
  if (!VERIFIED_DOMAIN_ID || !AUTH_TOKEN) {
    throw new Error('VERIFIED_DOMAIN_ID and AUTH_TOKEN env vars are required for Phase 2 scans.');
  }

  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${AUTH_TOKEN}`,
  };

  // 1. Trigger the scan
  const startedAt = Date.now();
  const triggerRes = http.post(
    `${BASE_URL}/api/v1/scans/`,
    JSON.stringify({
      domain: TARGET_DOMAIN,
      scan_type: 'active_vulnerability',
      verified_domain_id: VERIFIED_DOMAIN_ID,
    }),
    { headers },
  );

  const triggered = check(triggerRes, {
    'scan triggered (202)': (r) => r.status === 202,
  });

  if (!triggered) {
    console.error(`Trigger failed: ${triggerRes.status} ${triggerRes.body}`);
    return;
  }

  const scanId = triggerRes.json('scan_id');

  

  console.log(`Phase 2 scan ${scanId}: ${finalStatus ?? 'timeout'} in ${elapsedMs}ms`);
}