const API_BASE = "/api/domains";
export type domain_verification_status = "pending" | "verified" | "failed" | "expired";
export type DomainVerificationCode = | "verified" | "record_not_found" | "token_mismatch" | "lookup_failed";
export type domain_sort_field = "domain" | "create_at" | "status";
export type sort_order = "asc" | "desc";

export interface VerifiedDomain {
    id: string;
    domain: string;
    status: domain_verification_status;
    verification_tole: string;
    verified_at: string | null;
}

export type domain_item = {
    id: string;
    domain: string;
    status: domain_verification_status;
    verification_method: string;
    verification_token: string;
    created_at: string;
    verified_at: string | null;
    last_checked_at: string | null;
    last_verification_code : DomainVerificationCode | null;
};

export type domain_counts = {
    all : number;
    pending: number;
    verified: number;
    failed: number;
    expired: number;
};

export type domain_pagination = {
    total : number;
    limit: number;
    offset: number;
    has_more: boolean;
};

export interface DomainList {
    items: domain_item[];
    counts: domain_counts;
    pagination: domain_pagination;
}

export interface ListDomainsParams {
    status?: domain_verification_status;
    search?: string;
    sort?: domain_sort_field;
    order?: sort_order;
    limit?: number;
    offset?: number;
}

async function parseError(response: Response, fallback: string): Promise<Error> {
    const body = await response.json().catch(() => ({ detail: fallback}));
    return new Error(body.detail ?? fallback);
}

export async function fetch_domains(params: ListDomainsParams = {}): Promise<DomainList> {
    const query = new URLSearchParams;
    if (params.status) query.set("status", params.status);
    if (params.search) query.set("search", params.search);
    if (params.sort) query.set("sort", params.sort);
    if (params.order) query.set("order", params.order);
    if (params.limit !== undefined) query.set("limit", String(params.limit));
    if (params.offset !== undefined) query.set("offset", String(params.offset));

    const qs = query.toString();
    const response = await fetch(`${API_BASE}${qs ? `?${qs}` : ""}`);
    if(!response.ok) throw await parseError(response, "Failed to load domains");
    return response.json();
}

export async function add_domain(domain: string): Promise<VerifiedDomain> {
    const response = await fetch(API_BASE, {
        method: "POST",
        headers: {"Content-Type" : "application/json"},
        body: JSON.stringify({domain}),
    });
    if(!response.ok) throw await parseError(response, "Failed to add domain");
    return response.json();

}