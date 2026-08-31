//control data going into service delivery

export type EngagementStatus =
    | "requested"
    | "scoping"
    | "scheduled"
    | "in_progress"
    | "review"
    | "completed"
    | "cancelled";

export type AssessmentType = "web_application" | "mobile_application" | "api" | "network" | "cloud" | "other";

export type EngagementType = "black_box" | "grey_box" | "white_box";

export type Severity = "info" | "low" | "medium" | "high" | "critical";

export type FindingStatus = "open" | "in_progress" | "resolved" | "accepted_risk" | "false_positive";

export type RetestStatus = "requested" | "in_progress" | "resolved" | "still_vulnerable";

export type EngagementMessageChannel = "client_service_delivery" | "service_delivery_pentester";

//reusable object

export interface UserSummary {
    id: string;
    full_name: string | null;
    email: string | null;
    role: string | null;
}

export interface Pagination {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
}

export interface EngagementActionResponse {
    id: string;
    status: EngagementStatus;
    service_delivery_id?: string | null;
    assigned_pentester_id?: string | null;
    scheduled_start_date?: string | null;
    scheduled_end_date?: string | null;
    reviewed_at?: string | null;
    completed_at?: string | null;
    updated_at: string;
}

//list engagement  feature

export interface EngagementListFilters {
    status?: EngagementStatus;
    assessment_type?: AssessmentType;
    search?: string;
    pentester_id?: string;
    assigned?: boolean;
    limit?: number;
    offset?: number;
}

export interface EngagementListItem {
    id: string;
    title: string;
    client: UserSummary;
    engagement_type: EngagementType;
    assessment_type: AssessmentType;
    priority: string;
    status: EngagementStatus;
    service_delivery?: UserSummary | null;
    assigned_pentester?: UserSummary | null;
    requested_start_date?: string | null;
    requested_end_date?: string | null;
    scheduled_start_date?: string | null;
    scheduled_end_date?: string | null;
    final_quote?: string | null;
    created_at: string;
    updated_at: string;
}

export interface EngagementListResponse {
    items: EngagementListItem[];
    pagination: Pagination;
}

//engagement detail