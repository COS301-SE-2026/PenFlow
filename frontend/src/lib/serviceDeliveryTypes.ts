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

export interface EngagementAsset {
    id: string;
    identifier: string;
    asset_type: string;
    asset_metadata: Record<string, unknown>;
    verified_domain_id?: string | null;
}

export interface FindingSummary {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    with_evidence: number;
}

export interface RetestSummary {
    total: number;
    requested: number;
    in_progress: number;
    resolved: number;
    still_vulnerable: number;
}

export interface EngagementDetail {
    id: string;
    title: string;
    engagement_type: EngagementType;
    assessment_type: AssessmentType;
    priority: string;
    status: EngagementStatus;
    scope: string;
    objective?: string | null;
    constraints?: string | null;
    primary_contact?: string | null;
    estimated_quote: string;
    final_quote?: string | null;
    estimated_duration_days?: number | null;
    requested_start_date?: string | null;
    requested_end_date?: string | null;
    scheduled_start_date?: string | null;
    scheduled_end_date?: string | null;
    started_at?: string | null;
    completed_at?: string | null;
    reviewed_by?: UserSummary | null;
    reviewed_at?: string | null;
    review_note?: string | null;
    client: UserSummary;
    service_delivery?: UserSummary | null;
    assigned_pentester?: UserSummary | null;
    assets: EngagementAsset[];
    finding_summary: FindingSummary;
    retest_summary: RetestSummary;
    created_at: string;
    updated_at: string;
}

//Mutation request bodies
export interface EngagementScopingUpdate {
    assessment_type?: AssessmentType | null;
    scope?: string | null;
    objective?: string | null;
    constraints?: string | null;
    final_quote?: string | null;
    estimated_duration_days?: number | null;
}

export interface AssignPentesterRequest {
    pentester_id: string;
}

export interface ScheduleEngagementRequest {
    scheduled_start_date: string;
    scheduled_end_date: string;
}
export interface ReassignEngagementRequest {
    pentester_id: string;
    reason: string;
}

export interface RescheduleEngagementRequest {
    scheduled_start_date: string;
    scheduled_end_date: string;
    reason: string;
}

export interface ReturnFromReviewRequest {
    review_note: string;
}

export interface CancelEngagementRequest {
    reason: string;
}

//dashboard
export interface DashboardCounts {
    requested: number;
    scoping: number;
    scheduled: number;
    in_progress: number;
    review: number;
    completed: number;
    cancelled: number;
    needs_attention: number;
}

export interface DashboardEngagementItem {
    id: string;
    title: string;
    status: EngagementStatus;
    assessment_type: AssessmentType;
    priority: string;
    client: UserSummary;
    service_delivery?: UserSummary | null;
    assigned_pentester?: UserSummary | null;
    scheduled_start_date?: string | null;
    scheduled_end_date?: string | null;
    updated_at: string;
}

export interface DashboardResponse {
    counts: DashboardCounts;
    unclaimed_requests: DashboardEngagementItem[];
    awaiting_review: DashboardEngagementItem[];
    upcoming_engagements: DashboardEngagementItem[];
}

