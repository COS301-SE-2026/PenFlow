//business logic

import type {
    ActivityListResponse,
    AssignPentesterRequest,
    AuditListFilters,
    CancelEngagementRequest,
    ConversationListResponse,
    DashboardResponse,
    EngagementActionResponse,
    EngagementDetail,
    EngagementListFilters,
    EngagementListResponse,
    EngagementMessage,
    EngagementMessageChannel,
    EngagementMessageCreate,
    EngagementMessageListResponse,
    EngagementScopingUpdate,
    FindingDetail,
    FindingListFilters,
    FindingListResponse,
    MarkReadResponse,
    PentesterCreateRequest,
    PentesterDetail,
    PentesterListFilters,
    PentesterListResponse,
    ReassignEngagementRequest,
    RescheduleEngagementRequest,
    Retest,
    RetestListResponse,
    ReturnFromReviewRequest,
    ScheduleEngagementRequest,
    UserSummary,

} from "@/lib/serviceDeliveryTypes";
import { waapi } from "animejs";
import { URLSearchParams } from "next/dist/compiled/@edge-runtime/primitives/url";

type QueryValue = string | number | boolean | undefined | null ;

function buildQuery(params: Record<string, QueryValue>): string {
    const search = new URLSearchParams();
    for(const [key, value] of Object.entries(params)){
        if (value !== undefined && value !== null) search.set(key, String(value));
    }
    const qs = search.toString();
    return qs ? `?${qs}` : "";
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(path,{
        ...init,
        headers: {
            ...(init.body ? {"Content-Type": "application/json"}: {}),
            ...init.headers,
        },
    });

    const body = await response.json().catch(()=> null);
    if(!response.ok){
         const detail = typeof body?.detail === "string" ? body.detail : `Request failed with status ${response.status}.`;
         throw new Error(detail);
    }
    return body as T;
}

//GET /engagements
export async function listEngagements(filters: EngagementListFilters = {}): Promise<EngagementListResponse> {
    const query = buildQuery({
        status: filters.status,
        assessment_type: filters.assessment_type,
        search: filters.search,
        pentester_id: filters.pentester_id,
        assigned: filters.assigned,
        limit: filters.limit,
        offset: filters.offset,
    });
    return apiFetch(`/api/service-delivery/engagements${query}`);
}

// GET /engagements/{engagement_id}
export async function getEngagementDetail(engagementId: string): Promise<EngagementDetail> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}`);
}

// POST /engagements/{engagement_id}/claim
export async function claimEngagement(engagementId: string): Promise<EngagementActionResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/claim`, { method: "POST" });
}

//PATCH /engagements/{engagement_id}/scoping
export async function updateEngagementScoping((engagementId: string, body: EngagementScopingUpdate): Promise<EngagementActionResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/scoping`, {
        method: "PATCH",
        body: JSON.stringify(body),
    });
}