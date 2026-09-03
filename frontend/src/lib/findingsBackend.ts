import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";

export async function proxyToFindingsApi(
    path:string,
    init:RequestInit = {},
){
    return authenticatedBackendRequest({
        path:`/api/v1/findings${path}`,
        init,
    });
}
