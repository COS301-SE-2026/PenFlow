import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'https://pen-flow.com';

export const options = {
  scenarios: {
    //QR1 :P95 API response time under 2s under normal load
    perfromance :{
      executor: 'constant-vus', //constant vus 
      vus:10, //10 virtual user
      duration: '30s',
      exec: 'checkHealth',
    },
    // QR-03: system stays stable at 100 concurrent user
    scalability: {
    executor: 'ramping-vus',//ramping vus
    startVUs: 0,
    stages: [
      { duration: '30s', target: 100 },
      { duration: '1m', target: 100 },
      { duration: '30s', target: 0 },
    ],
    exec: 'checkHealth',
    }
  },
   thresholds: {
  http_req_duration: ['p(95)<2000'],//qr 1 target 95 % chance less than 2ms
   http_req_failed: ['rate<0.01'], //qr2 target 
  },
};

export function checkHealth(){
  const res = http.get(`${BASE_URL}/api/v1/health`)
  check(res,{
    'status is 200': (r) => r.status === 200,
  });
}