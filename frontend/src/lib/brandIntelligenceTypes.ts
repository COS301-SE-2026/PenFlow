export type brand_risk_level = "low" | "medium" | "high" | "critical";
export type brand_candidate_status = "new" | "under_review" | "confirmed_impersonation" | "false_positive" | "resolved";


//the mutation
export interface brand_mutation_evidence
{
    candidate_domain?: string;
    normalized_domain?: string;
    mutation_type?: string;
    mutation_detail?: string;
    [key: string]: unknown;
}


//the public info gathered by the worker
export interface brand_signal_evidence
{
    is_resolvable?: boolean;
    ip_addresses?: string[];
    has_mx?: boolean;
    mx_records?: string[];
    has_tls?: boolean;
    tls_issuer?: string | null;
    creation_date?: string | null;
    days_old?: number | null;
    is_newly_registered?: boolean;
    geo_location?: string | null;
    isp?: string | null;
    [key: string]: unknown;
}


export interface brand_weights_applied
{
    base_mutation?: string;
    resolvable?: boolean;
    mx_enabled?: boolean;
    tls_enabled?: boolean;
    newly_registered?: boolean;
    [key: string]: unknown;
}


//the backend can return partial evidence when a lookup fails
export interface brand_evidence
{
    mutation?: brand_mutation_evidence;
    signals?: brand_signal_evidence;
    reasons?: string[];
    weights_applied?: brand_weights_applied;
    [key: string]: unknown;
}


export interface brand_candidate
{
    id: string;
    brand_monitoring_id: string;
    candidate_domain: string;
    normalized_domain: string;
    risk_score: number;
    risk_level: brand_risk_level;
    status: brand_candidate_status;
    evidence: brand_evidence;
    first_seen: string;
    last_seen: string;
    resolved_at: string | null;
}


export interface brand_monitoring
{
    id: string;
    verified_domain_id: string;
    is_active: boolean;
    last_run_at: string | null;
    next_run_at: string | null;
    created_at: string;
    candidates: brand_candidate[];
}


export interface brand_status_update
{
    status: brand_candidate_status;
}
