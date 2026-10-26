import { NextResponse } from "next/server";

import {
    fetchPublicScansApi,
    guestScanCookieName,
    isValidScanId,
    proxyToScansApi,
} from "@/lib/scansBackend";
import {
    rateLimitResponseHeaders,
} from "@/lib/clientIpForwarding";

export async function GET() {
    return proxyToScansApi("/");
}

export async function POST(req: Request) {
    const upstream = await fetchPublicScansApi("/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: await req.text(),
    });

    const body = await upstream.json().catch(() => null);

    if (!body || typeof body !== "object") {
        return NextResponse.json(
            { detail: "Invalid response from scan service" },
            {
                status: 502,
                headers: { "Cache-Control": "no-store" },
            },
        );
    }

    const {
        guest_token,
        guest_token_expires_in,
        ...publicBody
    } = body;

    const response = NextResponse.json(publicBody, {
        status: upstream.status,
        headers: rateLimitResponseHeaders(upstream),
    });

    if (
        upstream.ok
        && typeof guest_token === "string"
        && typeof guest_token_expires_in === "number"
        && guest_token_expires_in > 0
        && typeof publicBody.scan_id === "string"
        && isValidScanId(publicBody.scan_id)
    ) {
        response.cookies.set(
            guestScanCookieName(publicBody.scan_id),
            guest_token,
            {
                httpOnly: true,
                secure: process.env.NODE_ENV === "production",
                sameSite: "lax",
                path: `/api/scans/${publicBody.scan_id}`,
                maxAge: Math.min(
                    guest_token_expires_in,
                    24 * 60 * 60,
                ),
            },
        );
    }

    return response;
}