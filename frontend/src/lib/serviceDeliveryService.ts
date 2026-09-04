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
    ReportResponse,
    RescheduleEngagementRequest,
    Retest,
    RetestListResponse,
    ReturnFromReviewRequest,
    ScheduleEngagementRequest,

} from "@/lib/serviceDeliveryTypes";


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

//GET /engagements/{engagement_id}
export async function getEngagementDetail(engagementId: string): Promise<EngagementDetail> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}`);
}

//POST /engagements/{engagement_id}/claim
export async function claimEngagement(engagementId: string): Promise<EngagementActionResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/claim`, { method: "POST" });
}

//PATCH /engagements/{engagement_id}/scoping
export async function updateEngagementScoping(engagementId: string, body: EngagementScopingUpdate): Promise<EngagementActionResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/scoping`, {
        method: "PATCH",
        body: JSON.stringify(body),
    });
}

// PUT /engagements/{engagement_id}/pentester
export async function assignPentester(engagementId: string, body: AssignPentesterRequest): Promise<EngagementActionResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/pentester`, {
        method: "PUT",
        body: JSON.stringify(body),    
    });    
}

//POST /engagements/{engagement_id}/schedule
export async function scheduleEngagement(engagementId: string, body: ScheduleEngagementRequest): Promise<EngagementActionResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/schedule`, {
        method: "POST",
        body: JSON.stringify(body), 
    });
}

// POST /engagements/{engagement_id}/reassign
export async function reassignEngagement(engagementId: string, body: ReassignEngagementRequest): Promise<EngagementActionResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/reassign`, {
        method: "POST",
        body: JSON.stringify(body),
    });
}

// POST /engagements/{engagement_id}/reschedule
export async function rescheduleEngagement(engagementId: string, body: RescheduleEngagementRequest): Promise<EngagementActionResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/reschedule`, {
        method: "POST",
        body: JSON.stringify(body),
    });
}

// POST /engagements/{engagement_id}/review/return
export async function returnEngagementFromReview(engagementId: string, body: ReturnFromReviewRequest): Promise<EngagementActionResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/review/return`, {
        method: "POST",
        body: JSON.stringify(body),
    });
}

// POST /engagements/{engagement_id}/review/complete
export async function completeEngagementReview(engagementId: string): Promise<EngagementActionResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/review/complete`, { method: "POST" });
}

// POST /engagements/{engagement_id}/cancel
export async function cancelEngagement(engagementId: string, body: CancelEngagementRequest): Promise<EngagementActionResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/cancel`, {
        method: "POST",
        body: JSON.stringify(body),
    });
}

// GET /dashboard
export async function getDashboard(): Promise<DashboardResponse> {
    return apiFetch("/api/service-delivery/dashboard");
}

// GET /pentester
export async function listPentesters(filters: PentesterListFilters = {}): Promise<PentesterListResponse> {
    const query = buildQuery({
        search: filters.search,
        assessment_type: filters.assessment_type,
        availability_status: filters.availability_status,
        is_active: filters.is_active,
        limit: filters.limit,
        offset: filters.offset,
    });
    return apiFetch(`/api/service-delivery/pentesters${query}`);
}

// GET /pentesters/{pentester_id}
export async function getPentesterDetail(pentesterId:string): Promise<PentesterDetail> {
    return apiFetch(`/api/service-delivery/pentesters/${pentesterId}`);
}

// DELETE /pentesters/{pentester_id}
export async function deletePentester(
    pentesterId: string,
): Promise<void> {
    await apiFetch<void>(
        `/api/service-delivery/pentesters/${pentesterId}`,
        {
            method: "DELETE",
        },
    );
}

// POST /pentesters
export async function createPentester(payload: PentesterCreateRequest): Promise<void> {
    await apiFetch<unknown>(
        "/api/service-delivery/pentesters",
        {
            method: "POST",
            body: JSON.stringify(payload),
        },
    );
}

//GET /engagements/{engagement_id}/findings
export async function listEngagementFindings(engagementId: string, filters: FindingListFilters = {}): Promise<FindingListResponse>{
    const query = buildQuery({
        severity: filters.severity,
        status: filters.status,
        limit: filters.limit,
        offset: filters.offset,
    });
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/findings${query}`);
}

//GET /engagements/{engagement_id}/findings/{finding_id}
export async function getEngagementFinding(engagementId: string, findingId: string): Promise<FindingDetail>{
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/findings/${findingId}`);
}

//GET /evidence/{evidence_id}/download
export async function downloadEvidence(evidenceId: string,_fileName: string):Promise<Blob> {
const response = await fetch(`/api/service-delivery/evidence/${evidenceId}/download`);
if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail : "Failed to download evidence.");
    }
    return response.blob();
}

// GET /engagements/{engagement_id}/retests
export async function listEngagementRetests(engagementId: string): Promise<RetestListResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/retests`);
}

// GET /retests/{retest_id}
export async function getRetestDetail(retestId: string): Promise<Retest> {
    return apiFetch(`/api/service-delivery/retests/${retestId}`);
}

// GET /messages
export async function listConversations(): Promise<ConversationListResponse> {
    return apiFetch("/api/service-delivery/messages");
}

// GET /api/v1/engagements/{engagement_id}/messages?channel=
export async function listConversationMessages(engagementId: string, channel: EngagementMessageChannel): Promise<EngagementMessageListResponse> {
    return apiFetch(`/api/engagements/${engagementId}/messages${buildQuery({ channel })}`);
}

// POST /api/v1/engagements/{engagement_id}/messages
export async function sendConversationMessage(engagementId: string, body: EngagementMessageCreate): Promise<EngagementMessage> {
    return apiFetch(`/api/engagements/${engagementId}/messages`, {
        method: "POST",
        body: JSON.stringify(body),
    });
}

// PATCH /api/v1/engagements/{engagement_id}/messages/read?channel=
export async function markConversationRead(engagementId: string, channel: EngagementMessageChannel): Promise<MarkReadResponse> {
    return apiFetch(`/api/engagements/${engagementId}/messages/read${buildQuery({ channel })}`, { method: "PATCH" });
}

// GET /audit
export async function listAuditActivity(filters: AuditListFilters = {}): Promise<ActivityListResponse> {
    const query = buildQuery({ limit: filters.limit, offset: filters.offset });
    return apiFetch(`/api/service-delivery/audit${query}`);
}

//GET /engagements/{engagement_id}/report
export async function getEngagementReport(engagementId: string): Promise<ReportResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/report`);
}

//POST /engagements/{engagement_id}/report/retry 
export async function retryEngagementReport(engagementId: string): Promise<ReportResponse> {
    return apiFetch(`/api/service-delivery/engagements/${engagementId}/report/retry`, { method: "POST" });
}

//GET /reports/{report_id}/download
export async function downloadReport(reportId: string): Promise<Blob> {
    const response = await fetch(`/api/service-delivery/reports/${reportId}/download`);
    if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail : "Failed to download report.");
    }
    return response.blob();
}