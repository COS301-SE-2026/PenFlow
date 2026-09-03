import http from 'k6/http';
import { check } from 'k6';

// QR-08: Unauthenticated requests return 401; cross-user requests return 404
//        (not 403 - ownership is enforced by a user_id-scoped lookup that
//        returns "not found" rather than an explicit "forbidden").
// QR-09: Rate limiter returns 429 on the 4th scan submission from the same
//        IP within 10 minutes
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3001';
const AUTH_TOKEN = __ENV.AUTH_TOKEN; // optional - needed only for the cross-user check

const SECRET_PATTERNS = [
  /postgresql:\/\//i,
  /amqp:\/\//i, // AMQP/RabbitMQ connection strings  
  /secret/i, // // Any mention of "secret"
  /api[_-]?key/i,
  /password/i,
  /traceback/i,
  /BEGIN (RSA|PRIVATE) KEY/i,
];

function bodyLeaksSecrets(body) {
  return SECRET_PATTERNS.some((pattern) => pattern.test(body));
}

export const options = {
  vus: 1,
  iterations: 1,
};

export default function () {
  // --- QR-08a unauthenticated request to a protected endpoint  401 
  const domainsRes = http.get(`${BASE_URL}/api/v1/domains`);
  check(domainsRes, {
    'unauthenticated request returns 401': (r) => r.status === 401,
    'no secrets leaked in 401 body': (r) => !bodyLeaksSecrets(r.body),
  });

  // --- QR-09a: rate limiter -> 429 on the 4th scan submission ---
  // Request #1 is authenticated (if AUTH_TOKEN is set) so its scan_id can be
  // reused for the QR-08b cross-user check below, without spending extra quota.
  let ownedScanId = null;
  let sawRateLimit = false;

  for (let i = 1; i <= 4; i++) {
    const headers = { 'Content-Type': 'application/json' };
    if (i === 1 && AUTH_TOKEN) {
      headers.Authorization = `Bearer ${AUTH_TOKEN}`;
    }

    const res = http.post(
      `${BASE_URL}/api/v1/scans/`,
      JSON.stringify({ domain: 'example.com', scan_type: 'passive_ctem' }),
      { headers },
    );

    if (i <= 3) {
      check(res, { [`request ${i}/4 accepted (202)`]: (r) => r.status === 202 });
      if (i === 1 && res.status === 202) {
        ownedScanId = res.json('scan_id');
      }
    } else {
      sawRateLimit = check(res, { 'request 4/4 rate-limited (429)': (r) => r.status === 429 });
      check(res, { 'no secrets leaked in 429 body': (r) => !bodyLeaksSecrets(r.body) });
    }
  }

  console.log(`Rate limit triggered on 4th request: ${sawRateLimit}`);

  // QR-08b: cross-user / anonymous access to another user's scan 404 
  if (!AUTH_TOKEN) {
    console.warn('AUTH_TOKEN not set - skipping QR-08b cross-user check');
  } else if (!ownedScanId) {
    console.warn('First scan request did not return a scan_id - skipped QR-08b');
  } else {
    // query the owned scan with NO auth - should not reveal it exists
    const crossUserRes = http.get(`${BASE_URL}/api/v1/scans/${ownedScanId}/status`);
    check(crossUserRes, {
      'cross-user/anonymous access to owned scan returns 404': (r) => r.status === 404,
      'no secrets leaked in 404 body': (r) => !bodyLeaksSecrets(r.body),
    });
  }
}