import {cookies} from "next/headers";
import {NextResponse} from "next/server";

const BACKEND_URL = process.env.API_URL ?? "http://localhost:3001";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isValidDomainId(value: string): boolean {
    return UUID_PATTERN.test(value);
}

export async function proxyToDomainsApi(path: string, init:RequestInit = {}): Promise<NextResponse> {
    const accessToken = (await cookies()).get("access_token")?.value;
    const response = await fetch(`${BACKEND_URL}/api/v1/scans${path}`, {
        ...init,
        headers: {
            ...init.headers,
            ...(accessToken ? {Authorization: `Bearer ${accessToken}`} : {}),
        },
        cache: "no-store",
    });

    if(response.status === 204) { 
        return new NextResponse(null, {status:204});
    }

    const body = await response.json().catch(() => null);
    if(response.status >= 500) {
        console.error(`[scans proxy] backend ${response.status} for ${path}:`, body);
        return NextResponse.json(
            {detail: "Something went wrong. Please try again later."},
            {status: response.status}
        );
    }
    return NextResponse.json(body, {status: response.status});
}