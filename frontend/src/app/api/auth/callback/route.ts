import { NextRequest, NextResponse } from "next/server";

import { setAuthCookies } from "@/lib/authSession";
import { exchangeAuthCode } from "@/lib/keycloakService";

const BACKEND_URL = process.env.API_URL ?? "http://localhost:3001";
const APP_URL = process.env.APP_URL ?? "http://localhost:3000";

export async function GET(req: NextRequest) {
    const code = req.nextUrl.searchParams.get("code");
    const returnedState = req.nextUrl.searchParams.get("state");

    const expectedState = req.cookies.get("oauth_state")?.value;
    const verifier = req.cookies.get("pkce_verifier")?.value;

    if (!code || !returnedState || !expectedState || returnedState !== expectedState || !verifier) {
        return NextResponse.json(
            { error: "Invalid authentication callback" },
            { status: 400 },
        );
    }

    const redirectUri = `${APP_URL}/api/auth/callback`

    try {
        const tokens = await exchangeAuthCode(code, verifier, redirectUri);

        const resp = NextResponse.redirect(
            new URL("/", APP_URL),
        );

        setAuthCookies(resp, tokens);

        resp.cookies.delete("oauth_state");
        resp.cookies.delete("pkce_verifier");

        const provisionRes = await fetch(
            `${BACKEND_URL}/api/v1/users/me`,
            {
                headers: {
                    Authorization: `Bearer ${tokens.access_token}`,
                },
            },
        );

        if (!provisionRes.ok) {
            const body = await provisionRes.text();

            console.error(`[auth] provisioning returned ${provisionRes.status}:`, body);

            throw new Error("Failed to provision user.");
        }

        return resp;
    } catch(err) {
        console.error("[auth] callback failed: ", err);

        const resp = NextResponse.redirect(
            new URL("/?auth_error=1", APP_URL),
        );

        resp.cookies.delete("oauth_state");
        resp.cookies.delete("pkce_verifier");
        resp.cookies.delete("access_token");
        resp.cookies.delete("refresh_token");
        resp.cookies.delete("id_token");
        resp.cookies.delete("logged_in");
        resp.cookies.delete("access_token_expires_at");

        return resp;
    }
}