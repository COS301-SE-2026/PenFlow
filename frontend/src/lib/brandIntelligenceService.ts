import { authenticatedFetch } from "@/lib/authFetch";
import type
{
    brand_candidate,
    brand_candidate_status,
    brand_monitoring,
} from "@/lib/brandIntelligenceTypes";
const API_BASE = "/api/brand-intelligence";


//helper so we handel the errors uniformly for the backend
async function parse_error
(
    response: Response,
    fallback: string,
): Promise<Error>
{
    const body = await response
        .json()
        .catch(() => ({ detail: fallback }));

    return new Error
    (
        typeof body?.detail === "string"
            ? body.detail
            : fallback,
    );
}

//load the current monitoring state and candidates for a verified domain
export async function fetch_brand_monitoring
(
    domain_id: string,
): Promise<brand_monitoring>
{
    const response = await authenticatedFetch(`${API_BASE}/domain/${domain_id}`);

    if (!response.ok)
    {
        throw await parse_error
        (
            response,
            "Failed to load brand monitoring",
        );
    }
    return response.json();
}


//start/restart monitoring for a verified domain
export async function trigger_brand_monitoring
(
    domain_id: string,
): Promise<brand_monitoring>
{
    const response = await authenticatedFetch
    (`${API_BASE}/trigger/${domain_id}`, {method: "POST"});

    if (!response.ok)
    {
        throw await parse_error
        (
            response,
            "Failed to start brand monitoring",
        );
    }
    return response.json();
}


//persist the investigation status selected by usr
export async function update_brand_candidate_status
(
    candidate_id: string,
    status: brand_candidate_status,
): Promise<brand_candidate>
{
    const response = await authenticatedFetch
    (`${API_BASE}/candidate/${candidate_id}/status`,
        {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ status }),
        },
    );

    if (!response.ok)
    {
        throw await parse_error
        (
            response,
            "Failed to update candidate status",
        );
    }
    return response.json();
}