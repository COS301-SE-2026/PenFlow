import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export const BACKEND_URL = process.env.API_URL ?? "http://localhost:3001";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isValidEngagementId(value: string): boolean {
    return UUID_PATTERN.test(value);
}

export async function proxyToEngagementsApi(path: string, init: RequestInit ={}): Promise<NextResponse> {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access_token")?.value;

    const response = await fetch(`${BACKEND_URL}/api/v1${path}`, {
        ...init,
        headers: {
            ...init.headers,
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        cache: "no-store",
    });

    if (response.status === 204) {
        return new NextResponse(null, { status: 204 });
    }

    const body = await response.json().catch(() => null);
    if (response.status >= 500) {
        console.error(`[engagements proxy] backend ${response.status} for ${path}:`,  body);
        return NextResponse.json(
            { detail: "Something went wrong. Please try again later."},
            { status: response.status }
        );
    }
    return NextResponse.json(body, { status: response.status });
} 
