//const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "/api/scans";
const API_BASE = "/api/scans";

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

export interface StartScanParams {
  domain: string;
  scan_type?: "passive_ctem" | "active_vulnerability";
  verified_domain_id?: string;
  email?: string;
}

export interface DashboardFindingItem {
  id: string;
  title: string;
  cve_id: string | null;
  severity: string;
  cvss_score: number | null;
  source: string;
  asset_identifier: string | null;
  description: string | null;
  recommendation: string | null;
}

export interface FetchScanFindingsParams {
  severity?: string;
  limit?: number;
  offset?: number;
}

export async function fetchScanFindings(
  scanId: string,
  params: FetchScanFindingsParams = {}
): Promise<DashboardFindingItem[]> {
  const query = new URLSearchParams();
  if(params.severity) query.set("severity", params.severity);
  if(params.limit !== undefined) query.set("limit", String(params.limit));
  if(params.offset !== undefined) query.set("offset", String(params.offset));

  const qs = query.toString();
  const response = await fetch(`/api/scans/${scanId}/findings${qs ? `?${qs}` : ""}`);
  if (!response.ok) {
    const err = await response.json().catch(() => ({detail: "Failed to load scan findings"}));
    throw new Error(err.detail ?? "Failed to load scan findings");
  }
  return response.json();
}

export interface DashboardAssetItem {
  id: string;
  identifier: string;
  asset_type: string;
  findings_count: number;
}

export interface FetchScanAssetsParams {
  limit?: number;
  offset?: number;
}

export async function fetchScanAssets(
  scanId: string,
  params: FetchScanAssetsParams = {}
): Promise<DashboardAssetItem[]> {
  const query = new URLSearchParams();
  if(params.limit !== undefined) query.set("limit", String(params.limit));
  if(params.offset !== undefined) query.set("offset", String(params.offset));

  const qs = query.toString();
  const response = await fetch(`/api/scans/${scanId}/assets${qs ? `?${qs}` : ""}`);
  if (!response.ok) {
    const err = await response.json().catch(() => ({detail: "Failed to load scan assets"}));
    throw new Error(err.detail ?? "Failed to load scan assets");
  }
  return response.json();
}

export interface RiskHistoryItem {
  date: string;
  risk_score:number;
  total_findings: number;
}

export async function fetchScanRiskHistory(scanId: string): Promise<RiskHistoryItem[]> {
  const response = await fetch(`/api/scans/${scanId}/risk-history`);
  if(!response.ok) {
    const err = await response.json().catch(() => ({detail: "Failed to load risk history"}));
    throw new Error(err.detail ?? "Failed to load risk history");
  }
  return response.json();
}

export async function postScanRequest(params: StartScanParams ): Promise<ScanStartResponse> {
  const response = await fetch(API_BASE, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Scan request failed" }));
    throw new Error(err.detail ?? "Scan request failed");
  }

  return response.json();
}

export interface ServiceListItem {
  id: string;
  service_name: string;
  host: string;
  port: number;
  protocol: string;
  product: string | null;
  version: string | null;
  state: string;
  risk_level: string;
  asset_count: number;
  banner: string | null;
  created_at: string;
}

export interface ServiceSummaryCounts {
  total: number;
  tcp: number;
  udp: number;
  open: number;
  filtered: number
}

export interface ServiceListResponse {
  total: number;
  counts: ServiceSummaryCounts;
  items: ServiceListItem[];
}

export interface FetchScanServicesParams {
  protocol?: string;
  search?: string;
  sort_by?: string;
  limit?: number;
  offset?: number;
}

export async function fetchScanServices(
  scanId: string,
  params: FetchScanServicesParams = {}
): Promise<ServiceListResponse> {
  const query = new URLSearchParams();
  if(params.protocol) query.set("protocol", params.protocol);
  if(params.search) query.set("search", params.search);
  if(params.sort_by) query.set("sort_by", params.sort_by);
  if(params.limit !== undefined) query.set("limit", String(params.limit));
  if(params.offset !== undefined) query.set("offset", String(params.offset));

  const qs = query.toString();
  const response = await fetch(`/api/scans/${scanId}/services${qs ? `?${qs}` : ""}`);
  if(!response.ok) {
    const err = await response.json().catch(() => ({detail: "Failed to load scan services"}));
    throw new Error(err.detail ?? "Failed to load scan services");
  }
  return response.json();
}


export interface ScanHistoryItem {
  id: string;
  domain: string;
  created_at: string;
  status: string;
  scan_type: string;
  progress: number;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

export async function fetchScanHistory(): Promise<ScanHistoryItem[]> {
  const response = await fetch(API_BASE);
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Failed to load scan history" }));
    throw new Error(err.detail ?? "Failed to load scan history");
  }
  return response.json();
}

export async function fetchScanSummary(scanId: string): Promise<ExecutiveSummary> {
  const response = await fetch(`/api/scans/${scanId}/summary`, {
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Failed to load summary" }));
    throw new Error(err.detail ?? "Failed to load summary");
  }
  return response.json();
}

export function getReportPdfUrl(scanId: string): string {
  return `${API_BASE}/${scanId}/pdf`;
}

export const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ff5f4e",
  high: "#f08030",
  medium: "#f5c842",
  low: "#4ade80",
  info: "#4f9fff",
};

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  });
}

export interface ScanSourceStatus {
  source_name: string;
  status: string;
  error_message: string | null;
}

export interface RealTimeScanStatus {
  scan_id: string;
  domain: string;
  created_at:string;
  scan_type: string;
  status: string;
  progress: number;
  sources: ScanSourceStatus[];
  report_status: ReportStatus | null;
}

export async function fetchScanStatus(scanId: string): Promise<RealTimeScanStatus> {
  const response = await fetch(`${API_BASE}/${scanId}/status`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: "Unable to retrieve scan status",
    }));
    throw new Error(error.detail ?? "Unable to retrieve scan status");
  }
  return response.json();
}

export interface FindingsCount {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  total: number;
}

export interface ScanMetrics {
  risk_score: number;
  risk_level: string;
  findings: FindingsCount;
  assets: Record<string, number>;
  services: Record<string, number>;
  technologies: Record<string, number>;
}

export async function fetchScanMetrics(scanId: string): Promise<ScanMetrics> {
  const response = await fetch(`${API_BASE}/${scanId}/metrics`);
  
  if (!response.ok) {
    const err = await response.json().catch(() => ({detail: "Failed to load scan metrics"}));
    throw new Error(err.detail ?? "Failed to load scan metrics");
  }
  return response.json();
}

export async function sendReportEmail(scanId: string, email: string): Promise<void> {
  const response = await fetch(`${API_BASE}/${scanId}/email-report`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: "Failed to send report to email",
    }));

    throw new Error(error.detail ?? "Failed to send report to email");
  }
}