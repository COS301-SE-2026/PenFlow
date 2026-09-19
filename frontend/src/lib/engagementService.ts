export interface EngagementListItem {
    id: string;
    title: string;
    engagement_type: string;
    priority: string;
    status: string;
    requested_start_date: string | null;
    estimated_duration_days: number | null;
    updated_at: string;
    client_name: string;
    asset_count: number;
    target_date: string | null;
    estimated_quote: number | null;
    assigned_pentester_name: string | null;
    user_role: string;
}

export interface UserSummary {
    id: string;
    full_name: string | null; email: string | null;
    role: string | null;
}

export interface EngagementAsset {
    id: string;
    identifier: string;
    asset_type: string;
    asset_metadata: Record<string, unknown>; verified_domain_id: string | null;
}

export interface FindingListItem {
    id: string;
    engagement_id: string | null;
    engagement_asset_id: string | null;
    source: string;
    status: string;
    is_verified: boolean;
    severity: "critical" | "high" | "medium" | "low" | "info";
    cvss_score: number | null;
    cve_id: string | null;
    title: string;
    description: string | null;
    created_at: string;
    asset_identifier: string | null;
}

export interface PreviousScanSummary { 
    domain: string;
    completed_at: string | null; 
    relevant_findings: number; 
    reviewed_findings: number;
}

export interface EngagementDetail {
    id: string; title: string;
    engagement_type: string; assessment_type: string; priority: string; status: string;
    scope: string;
    estimated_quote: number;
    final_quote: number | null;
    estimated_duration_days: number | null;
    requested_start_date: string | null;
    requested_end_date: string | null;
    scheduled_start_date: string | null; scheduled_end_date: string | null;
    target_date: string | null;
    started_at: string | null;
    completed_at: string | null;
    reviewed_at: string | null;
    review_note: string | null;
    created_at: string;
    updated_at: string; client: UserSummary;
    service_delivery: UserSummary | null; assigned_pentester: UserSummary | null;
    assets: EngagementAsset[];
    counts: {
    assets: number;
    manual_findings: number;
    automated_findings: number;
};
    recent_findings: FindingListItem[];
    previous_scan: PreviousScanSummary | null;
}

export interface ActivityItemResponse {
    id: string;
    action: string;
    entity_type: string;
    entity_id: string | null;
    actor: { id: string; full_name: string | null } | null;
    metadata: Record<string, any>;
    created_at: string;
}

//for picking retest
export interface RetestEligibleFinding {
    id: string;
    title: string;
    severity: "critical" | "high" | "medium" | "low" | "info";
}

export interface ClientFindingItem {
    id: string;
    title: string;
    severity: "critical" | "high" | "medium" | "low" | "info";
    description: string | null;
    recommendation: string | null;
    retest_status: "requested" | "in_progress" | "resolved" | "still_vulnerable" | null;
    retest_notes: string | null;
    retest_completed_at: string | null;
}

export interface EngagementReport {
    id: string;
    report_id?: string | null;
    engagement_id?: string | null;
    version: number;
    status: "pending" | "generating" | "completed" | "failed";
    pdf_path: string | null;
    generated_at: string | null;
    error_message: string | null;
}

export interface EngagementMessage {
    id: string;
    engagement_id: string;
    finding_id: string | null; 
    user: UserSummary; 
    recipient: UserSummary; 
    channel: string;
    comment: string;
    is_read: boolean; created_at: string;
}

export async function fetchEngagements(): Promise<EngagementListItem[]> {
    const res = await fetch("/api/engagements");
    if (!res.ok) throw new Error("Failed to fetch engagements");
    const data = await res.json();
    return data.items || [];
}

export async function fetchEngagementActivity(id: string): Promise<ActivityItemResponse[]> {
    const res = await fetch(`/api/engagements/${id}/activity`);
    if (!res.ok) throw new Error("Failed to fetch activity");
    const data = await res.json();
    return data.items || [];
}

export async function fetchEngagement (id: string): Promise<EngagementDetail> {
    const res = await fetch(`/api/engagements/${id}`);
    if (!res.ok) throw new Error("Failed to fetch engagement");
    return res.json();
}
export async function fetchEngagementFindings (id: string, limit = 100): Promise<FindingListItem[]> { 
    const res = await fetch(`/api/engagements/${id}/findings?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to fetch findings");
    const data = await res.json();
    return data.items || [];
}
export async function fetchEngagementMessages (id: string): Promise<EngagementMessage[]> { 
    const res = await fetch(`/api/engagements/${id}/messages?channel=client_service_delivery`); 
    if (!res.ok) throw new Error("Failed to fetch messages");
    const data = await res.json();
    return data.items || [];
}
export async function sendEngagementMessage(id: string, comment: string): Promise<void> { 
    const res = await fetch(`/api/engagements/${id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment, channel: "client_service_delivery" }),
    });
    if (!res.ok) throw new Error("Failed to send message");
}
export async function markEngagementMessagesRead(id: string): Promise<void> {
    await fetch(`/api/engagements/${id}/messages/read?channel=client_service_delivery`, {
        method: "PATCH",
    }).catch(() => {});
}

export async function fetchEngagementReport(id: string): Promise<EngagementReport | null> {
    const res = await fetch(`/api/engagements/${id}/report`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error("Failed to fetch report");
    return res.json();
}
export async function downloadEngagementReport(reportId: string): Promise<Blob> {
    const res = await fetch(`/api/reports/${reportId}/download`);
    if (!res.ok) throw new Error("Failed to download report");
    return res.blob();
}
export async function fetchClientFindings(id: string): Promise<ClientFindingItem[]> {
    const res = await fetch(`/api/engagements/${id}/client-findings`);
    if (!res.ok) throw new Error("Failed to fetch findings");
    const data = await res.json();
    return data.items || [];
}
export async function fetchRetestEligibleFindings(id: string): Promise<RetestEligibleFinding[]> {
    const res = await fetch(`/api/engagements/${id}/retests/eligible`);
    if (!res.ok) throw new Error("Failed to fetch retest-eligible findings");
    const data = await res.json();
    return data.items || [];
}
export async function requestRetest(id: string, findingIds: string[]): Promise<{ engagement_status: string }> {
    const res = await fetch(`/api/engagements/${id}/retests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ finding_ids: findingIds }),
    });
    if (!res.ok) throw new Error("Failed to request retest");
    return res.json();
}