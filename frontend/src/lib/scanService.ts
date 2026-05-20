const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";

export interface ScanStartResponse {
    scan_id: string;
    status: string;
  }

export async function postScanRequest(domain: string): Promise<ScanStartResponse> {
    const response = await fetch(`${API_BASE}/scans/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domain }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Scan request failed" }));
      throw new Error(err.detail ?? "Scan request failed");
    }

    return response.json();
  }