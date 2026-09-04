import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";
export async function proxyToUsersApi(
    path: string,
    init: RequestInit = {},
) {
    return authenticatedBackendRequest({ 
        path: `/api/v1/users${path}`,
        init,
    });
}
