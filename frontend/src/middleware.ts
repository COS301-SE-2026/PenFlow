import { NextRequest, NextResponse } from "next/server";

import {
    applicationOrigin,
    isAllowedBrowserRequest,
} from "@/lib/browserSecurity";
import {
    buildContentSecurityPolicy,
    createNonce,
} from "@/lib/contentSecurityPolicy";

export function middleware(request: NextRequest) {
    let origin: string;
    let policy: string;
    let nonce: string;

    try {
        origin = applicationOrigin();
        nonce = createNonce();

        policy = buildContentSecurityPolicy({
            nonce,
            appUrl: origin,
            keycloakUrl: (
                process.env.KEYCLOAK_PUBLIC_URL
                ?? (
                    process.env.NODE_ENV === "production"
                    ? ""
                    : "http://localhost:8080"
                )
            ),
            development: (
                process.env.NODE_ENV === "development"
            ),
        });
    } catch {
        return NextResponse.json(
            {
                detail: "Browser security configuration is unavailable",
            },
            {
                status: 500,
                headers: {"Cache-Control": "no-store"},
            },
        );
    }

    let response: NextResponse;

    if (
        !isAllowedBrowserRequest(
            request.method,
            request.headers,
            origin,
        )
    ) {
        response = NextResponse.json(
            {
                detail: "Cross-site or unverifiable request rejected",
            },
            {status: 403},
        );
    } else {
        const requestHeaders = new Headers(request.headers);

        requestHeaders.set("x-nonce", nonce);
        requestHeaders.set("Content-Security-Policy", policy);

        response = NextResponse.next({
            request: {
                headers: requestHeaders,
            },
        });
    }

    response.headers.set(
        "Content-Security-Policy",
        policy,
    );

    response.headers.set(
        "Cache-Control",
        request.nextUrl.pathname.startsWith("/api/")
        ? "no-store"
        : "private, no-store",
    );

    if (origin.startsWith("https://")) {
        response.headers.set(
            "Strict-Transport-Security",
            "max-age=31536000",
        );
    }

    return response;
}

export const config = {
    matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
}