import { NextRequest } from "next/server";

import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";

export async function GET(request: NextRequest) {
    const query = request.nextUrl.searchParams.toString();

    return authenticatedBackendRequest({
        path: `/api/v1/notifications${query ? `?${query}` : ""}`,
    });
}