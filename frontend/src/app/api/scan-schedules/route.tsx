import { NextRequest } from "next/server";

import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";

const API_PATH = "/api/v1/scan-schedules";

export async function GET() {
    return authenticatedBackendRequest({
        path: API_PATH,
    });
}

export async function POST(request: NextRequest) {
    const body = await request.text()

    return authenticatedBackendRequest({
        path: API_PATH,
        init: {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body,
        },
    });
}