import {cookies} from "next/headers";
import {NextResponse} from "next/server";

import { setAuthCookies } from "@/lib/authSession";
import { refreshAccessToken, TokenResponse } from "@/lib/keycloakService";

export const BACKEND_URL = process.env.API_URL ?? "http://localhost:3001";

interface BackendRequestOptions {
    path: string;
    init?: RequestInit;
}

async function callBackend(url: string, accessToken: string, init: RequestInit): Promise<Response> {
    return fetch(url, {
        ...init,
        headers: {
            ...init.headers,
            Authorization: `Bearer ${accessToken}`,
        },
        cache: "no-store",
    });
}

export async function authenticatedBackendRequest({
    path, init = {}
}: BackendRequestOptions): Promise<NextResponse> {
    const cookieStore = await cookies();

    const accessToken = cookieStore.get("access_token")?.value;
    const refreshToken = cookieStore.get("refresh_token")?.value;

    if(!accessToken && !refreshToken) {
        return NextResponse.json(
            { detail: "Not authenticated" },
            { status: 401 },
        );
    }

    let response: Response;

    if(accessToken) {
        response = await callBackend(
            `${BACKEND_URL}${path}`,
            accessToken,
            init,
        );
    } else {
        response = new Response(null, {
            status: 401,
        });
    }

    if(response.status !== 401) {
        return backendResponseToNextResponse(
            response,
            path,
        );
    }

    if(!refreshToken) {
        return NextResponse.json(
            { detail: "Not authenticated" },
            { status: 401 },
        );
    }

    try {
        const tokens = await refreshAccessToken(refreshToken);

        const retryResponse = await callBackend(
            `${BACKEND_URL}${path}`,
            tokens.access_token,
            init,
        );

        const nextResponse = await backendResponseToNextResponse(
            retryResponse,
            path,
        );

        setAuthCookies(nextResponse, tokens);

        return nextResponse;
    } catch {
        const res = NextResponse.json(
            { detail: "Not authenticated" },
            { status: 401 },
        );

        res.cookies.delete("access_token");
        res.cookies.delete("refresh_token");
        res.cookies.delete("id_token");
        res.cookies.delete("logged_in");
        res.cookies.delete("access_token_expires_at");

        return res;
    }
}

async function backendResponseToNextResponse(response: Response, path: string): Promise<NextResponse> {
    if(response.status === 204) {
        return new NextResponse(null, {
            status: 204,
        });
    }

    const body = await response.json().catch(() => null);

    if(response.status >= 500) {
        console.error(`[backend proxy] backend ${response.status} for ${path}:`,
            body,
        );

        return NextResponse.json(
            {
                detail: "Something went wrong. Please try again later.",
            },
            {
                status: response.status,
            },
        );
    }

    return NextResponse.json(body, {
        status: response.status,
    });
}

export async function authenticatedBackendFetch(
    path: string,
    init: RequestInit = {},
): Promise<{
    response: Response;
    tokens?: TokenResponse;
}> {
    const cookieStore = await cookies();

    const accessToken = cookieStore.get("access_token")?.value;
    const refreshToken = cookieStore.get("refresh_token")?.value;

    if(!accessToken && !refreshToken) {
        return {
            response: new Response(null, {
                status: 401,
            }),
        };
    }

    let response: Response;

    if(accessToken) {
        response = await callBackend(
            `${BACKEND_URL}${path}`,
            accessToken,
            init,
        );
    } else {
        response = new Response(null, {
            status: 401,
        });
    }

    if(response.status !== 401) {
        return { response };
    }

    if(!refreshToken) {
        return { response };
    }

    try {
        const tokens = await refreshAccessToken(refreshToken);

        const retryResponse = await callBackend(
            `${BACKEND_URL}${path}`,
            tokens.access_token,
            init,
        );

        return {
            response: retryResponse,
            tokens,
        };
    } catch {
        return {
            response: new Response(null, {
                status: 401,
            }),
        };
    }
}