import { cookies } from "next/headers";
import { NextResponse } from "next/server";
//
const BACKEND_URL = process.env.API_URL ?? "http://localhost:3001";

export async function proxyReportBinary(path: string): Promise<Response> {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access_token")?.value;

    if (!accessToken) {
        return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/reports${path}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
        cache: "no-store",
    });
    if (!response.ok) {
        const body = await response.json().catch(() => null);
        return NextResponse.json(body ?? { detail: "Request failed." }, { status: response.status });
    }

    const headers = new Headers();
    const contentType = response.headers.get("content-type");
    const contentDisposition = response.headers.get("content-disposition");
    if (contentType) headers.set("content-type", contentType);
    if (contentDisposition) headers.set("content-disposition", contentDisposition);

    return new Response(response.body, { status: response.status, headers });
}