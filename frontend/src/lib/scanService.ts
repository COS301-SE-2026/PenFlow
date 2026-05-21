const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001/api/v1";

// --- Executive summary types ---

export interface ScanSummary {
  id: string;
  domain: string;
  status: string;
  progress: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface RiskSnapshot {
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
}

export interface TopFinding {
  id: string;
  severity: string;
  title: string;
  description: string | null;
  recommendation: string | null;
  source: string;
  asset_identifier: string | null;
  asset_type: string | null;
  created_at: string;
}

export interface AssetTypeBreakdown {
  asset_type: string;
  total_assets: number;
  affected_assets: number;
}

export interface AssetImpactSummary {
  total_assets_scanned: number;
  affected_assets_count: number;
  asset_type_breakdown: AssetTypeBreakdown[];
  top_affected_assets: {
    identifier: string;
    asset_type: string;
    finding_count: number;
    highest_severity: string;
  }[];
}

export interface ReportStatus {
  status: string;
  generated_at: string | null;
  pdf_path: string | null;
  error_message: string | null;
}

export interface ExecutiveSummary {
  scan_summary: ScanSummary;
  risk_snapshot: RiskSnapshot;
  top_findings: TopFinding[];
  asset_impact: AssetImpactSummary;
  report_status: ReportStatus | null;
}

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

export interface ScanHistoryItem {
  id: string;
  domain: string;
  created_at: string;
  status: string;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

export async function fetchScanHistory() {
  const response = await fetch(`${API_BASE}/scans/`);
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Failed to load scan history" }));
    throw new Error(err.detail ?? "Failed to load scan history");
  }
  return response.json();
}

export async function fetchScanSummary(scanId: string) {
  const response = await fetch(`${API_BASE}/scans/${scanId}/summary`);
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Failed to load summary" }));
    throw new Error(err.detail ?? "Failed to load summary");
  }
  return response.json();
}

export function getReportPdfUrl(scanId: string): string {
  return `${API_BASE}/scans/${scanId}/pdf`;
}