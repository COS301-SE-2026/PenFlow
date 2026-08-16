import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'https://pen-flow.com';

export const options = {
  scenarios: {
    //QR1 :P95 API response time under 2s under normal load
    perfromance :{
      executor: 'constant-vus',
      vus:10, //10 virtual user
      duration: '30s',
      exec: 'checkHealth',
    },
  },
   thresholds: {
  http_req_duration: ['p(95)<2000'],//qr 1 target
  },
};

export function checkHealth(){
  const res = http.get(`${BASE_URL}/api/v1/health`)
  check(res,{
    'status is 200': (r) => r.status === 200,
  });
}