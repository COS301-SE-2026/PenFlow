import { NextRequest, NextResponse } from "next/server";

import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

interface RouteContext {
    params: Promise<{schedule_id: string}>;
}

function invalidScheduleId() {
    return NextResponse.json(
        {
            detail: "Invalid schedule id",
        },
        {
            status: 400,
        },
    );
}

export async function GET(
    _request: NextRequest,
    context: RouteContext,
) {
    const {schedule_id } = await context.params;

    if(!UUID_PATTERN.test(schedule_id)) {
        return invalidScheduleId();
    }

    return authenticatedBackendRequest({
        path: `/api/v1/scan-schedules/${schedule_id}`,
    });
}

export async function PATCH(
    request: NextRequest,
    context: RouteContext,
) {
    const { schedule_id } = await context.params;

    if(!UUID_PATTERN.test(schedule_id)) {
        return invalidScheduleId();
    }

    const body = await request.text();

    return authenticatedBackendRequest({
        path: `/api/v1/scan-schedules/${schedule_id}`,
        init: {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
            },
            body,
        },
    });
}

export async function DELETE(
    _request: NextRequest,
    context: RouteContext,
) {
    const { schedule_id } = await context.params

    if(!UUID_PATTERN.test(schedule_id)) {
        return invalidScheduleId();
    }

    return authenticatedBackendRequest({
        path: `/api/v1/scan-schedules/${schedule_id}`,
        init: {
            method: "DELETE",
        },
    });
}