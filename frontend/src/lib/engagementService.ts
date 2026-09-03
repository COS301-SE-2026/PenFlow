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