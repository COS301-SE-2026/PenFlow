//frontend response check
export interface Pagination {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
}

//engagement status
export type EngagementStatus =
    | "requested"
    | "scoping"
    | "scheduled"
    | "in_progress"
    | "review"
    | "completed"
    | "cancelled";

export type EngagementType = "black_box" | "grey_box" | "white_box";

export interface PentesterWorkload {
    user_id: string;
    name: string;
    active_engagements: number;
    in_review: number;
    utilisation_percent: number;
}

export interface AdminAttentionEngagement {
    id: string;
    title: string;
    client_name: string;
    status: EngagementStatus;
    reason: string;
}


export interface AdminActivityItem {
    id: string;
    action: string;
    description: string;
    engagement_id: string;
    engagement_title: string;
    created_at: string;
}

export interface AdminDashboardResponse {
    period: { from: string; to: string };
    metrics: {
        total_engagements: number;
        in_progress: number;
        in_review: number;
        awaiting_assignment: number;
        review_actions: number;
    };
    engagement_status_counts: Record<EngagementStatus, number>;
    eview_queue: {
    engagements_awaiting_review: number;
    open_retests: number;
    reports_generating: number;
    overdue_engagements: number;
    };
    pentester_workload: PentesterWorkload[];
    engagements_requiring_attention: AdminAttentionEngagement[];
    recent_activity: AdminActivityItem[];
}

export interface AdminEngagementListItem {
    id: string;
    title: string;
    client: { user_id: string; name: string };
    engagement_type: EngagementType;
    status: EngagementStatus;
    assigned_to: { user_id: string; name: string } | null;
    target_completion_date: string | null;
    estimated_cost: string | null;
    currency: string;
    created_at: string;
    updated_at: string;
}