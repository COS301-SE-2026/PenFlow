import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isValidBrandId(value: string): boolean
{
    return UUID_PATTERN.test(value);
}

//all public brand requests use the existing cookie authentication and token refresh
export function proxyToBrandIntelligenceApi(path: string, init: RequestInit = {})
{
    return authenticatedBackendRequest
    ({
        path: `/api/v1/brand-intelligence${path}`,
        init,
    });
}
