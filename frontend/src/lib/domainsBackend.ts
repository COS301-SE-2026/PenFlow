import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isValidDomainId(value: string): boolean {
    return UUID_PATTERN.test(value);
}

export async function proxyToDomainsApi(
    path: string, 
    init: RequestInit = {},
) {
    return authenticatedBackendRequest({
        path: `/api/v1/domains${path}`,
        init,
    });
}

