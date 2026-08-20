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