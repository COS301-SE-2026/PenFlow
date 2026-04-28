export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001";
export const API_TIMEOUT = 30000;

export const API_ENDPOINTS = {
  auth: {
    register: "/api/auth/register",
    login: "/api/auth/login",
  },
  scans: {
    base: "/api/scans",  
    getById: (id: string) => `/api/scans/${id}`,  
  },
} as const;
