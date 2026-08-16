import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://pen-flow.com';

export const options = {
  scenarios: {
    //QR1 :P95 API response time under 2s under normal load
    perfromance :{
      executor: 'constant-vus',
      vus:10, //10 virtual user
      duration: '30s',
      exec: 'checkHealth',
    },
  }

}