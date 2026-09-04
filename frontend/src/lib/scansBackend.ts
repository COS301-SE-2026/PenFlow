import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { authenticatedBackendRequest, BACKEND_URL } from "./authenticatedBackend";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isValidScanId(
    value: string,
): boolean {
    return UUID_PATTERN.test(value);
}

export async function proxyToScansApi(
    path: string,
    init: RequestInit = {},
) {
    return authenticatedBackendRequest({
        path: `/api/v1/scans${path}`,
        init,
    });
}

export async function fetchPublicScansApi(
    path: string,
    init: RequestInit = {},
): Promise<Response> {
    const accessToken = (await cookies()).get("access_token")?.value
    const headers = new Headers(init.headers);

    if(accessToken) {
        headers.set("Authorization", `Bearer ${accessToken}`);
    }
    
    return fetch(`${BACKEND_URL}/api/v1/scans${path}`, {
        ...init,
        headers,
        cache: "no-store",
        });
}

export async function proxyToPublicScansApi(
    path: string,
    init: RequestInit = {},
): Promise<NextResponse> {
    const response = await fetchPublicScansApi(path, init);

    if(response.status === 204) {
        return new NextResponse(null, {status:204});
    }

    const body = await response.json().catch(() => null);

    if(response.status >= 500) {
        console.error(
            `[scans proxy] backend ${response.status} for ${path}:`,
            body,
        );

        return NextResponse.json(
            { detail: "Something went wrong. Please try again later." },
            { status: response.status },
        );
    }
    
    return NextResponse.json(body, { status: response.status });
}