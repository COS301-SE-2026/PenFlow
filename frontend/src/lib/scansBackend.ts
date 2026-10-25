import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { authenticatedBackendRequest, BACKEND_URL } from "./authenticatedBackend";
import {
    clientForwardingHeaders,
    rateLimitResponseHeaders,
} from "./clientIpForwarding";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isValidScanId(
    value: string,
): boolean {
    return UUID_PATTERN.test(value);
}

export async function proxyToScansApi(
    path: string,
    init: RequestInit = {},
): Promise<NextResponse> {
    const guestToken = await getGuestScanToken(path);

    if (guestToken) {
        return proxyToPublicScansApi(path, init);
    }

    const response = await authenticatedBackendRequest({
        path: `/api/v1/scans${path}`,
        init,
    });

    response.headers.set("Cache-Control", "no-store");

    return response;
}

export async function fetchPublicScansApi(
    path: string,
    init: RequestInit = {},
): Promise<Response> {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access_token")?.value;
    const guestToken = await getGuestScanToken(path);

    const headers = new Headers(init.headers);

    headers.delete("Authorization");
    headers.delete("X-Scan-Token");

    if (accessToken) {
        headers.set("Authorization", `Bearer ${accessToken}`);
    }

    if (guestToken) {
        headers.set("X-Scan-Token", guestToken);
    }

    const forwardedHeaders = await clientForwardingHeaders(
        init.method ?? "GET",
        `/api/v1/scans${path}`.split("?")[0],
    );

    for (const [name, value] of forwardedHeaders) {
        headers.set(name, value);
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
        return new NextResponse(null, 
            {
                status:204,
                headers: rateLimitResponseHeaders(response),
        });
    }

    const body = await response.json().catch(() => null);

    if(response.status >= 500) {
        console.error(
            `[scans proxy] backend ${response.status} for ${path}:`,
            body,
        );

        return NextResponse.json(
            { detail: "Something went wrong. Please try again later." },
            { 
                status: response.status ,
                headers: rateLimitResponseHeaders(response),
            },
        );
    }
    
    return NextResponse.json(body, {
        status: response.status,
        headers: rateLimitResponseHeaders(response),
    });
}

export function guestScanCookieName(scanId: string): string {
    return `penflow_guest_${scanId.toLowerCase()}`;
}

async function getGuestScanToken(
    path: string,
): Promise<string | undefined> {
    const scanId = path.split("/")[1];

    if (!scanId || !isValidScanId(scanId)) {
        return undefined;
    }

    return (await cookies()).get(
        guestScanCookieName(scanId),
    )?.value;
}