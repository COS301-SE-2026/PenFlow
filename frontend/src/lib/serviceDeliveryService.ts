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