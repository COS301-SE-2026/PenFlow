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