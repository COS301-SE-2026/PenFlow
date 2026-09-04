import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";

export async function proxyToRetestsApi(
    path:string,
    init:RequestInit = {},
){
    return authenticatedBackendRequest({
        path:`/api/v1/retests${path}`,
        init,
    });
}
