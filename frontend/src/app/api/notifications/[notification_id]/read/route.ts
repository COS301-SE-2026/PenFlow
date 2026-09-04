import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";

export async function PATCH(
    _request: Request,
    { params }: { params: Promise<{ notification_id: string }> },
) {

    const { notification_id } = await params;

    return authenticatedBackendRequest({
        path: `/api/v1/notifications/${notification_id}/read`,
        init: {
            method: "PATCH",
        },
    });
}