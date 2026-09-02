import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";

export async function PATCH() {
    return authenticatedBackendRequest({
        path: "/api/v1/notifications/read-all",
        init: {
            method: "PATCH",
        },
    });
}