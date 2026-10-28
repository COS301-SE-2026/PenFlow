import { createHmac } from "node:crypto";
import { isIP } from "node:net";
import { headers } from "next/headers";

const LOCAL_SECRET = "local-only-rate-limit-proxy-secret-change-for-production";

export function signedClientHeaders(
    incoming: Headers,
    method: string,
    path: string,
    source: string,
    secret: string,
    now = Math.floor(Date.now() / 1000),
): Headers {
    if (Buffer.byteLength(secret) < 32) {
        throw new Error(
            "Rate-limit proxy secret is not configured",
        );
    }

    let ip: string;

    if (source === "alb") {
        ip = incoming.get("x-forwarded-for")
        ?.split(",").at(-1)?.trim() ?? "";
    } else if (source === "local") {
        ip = "127.0.0.1";
    } else {
        throw new Error(
            "Client IP source must be configured",
        );
    }

    if (!isIP(ip) || ip.includes("%")) {
        throw new Error(
            "Invalid client address from trusted proxy",
        );
    }

    const timestamp = String(now);
    const message = (
        `${timestamp}\n`
        + `${method.toUpperCase()}\n`
        + `${path}\n`
        + ip
    );

    return new Headers({
        "X-PenFlow-Client-IP": ip,
        "X-PenFlow-Client-Time": timestamp,
        "X-PenFlow-Client-Signature": createHmac(
            "sha256",
            secret,
        ).update(message).digest("hex"),
    });
}

export async function clientForwardingHeaders(
    method: string,
    path: string,
): Promise<Headers> {
    const source = process.env.CLIENT_IP_SOURCE
    ?? (
        process.env.NODE_ENV === "production"
        ? ""
        : "local"
    );

    const secret = process.env.RATE_LIMIT_PROXY_SECRET
    ?? (
        process.env.NODE_ENV === "production"
        ? ""
        : LOCAL_SECRET
    );

    return signedClientHeaders(
        new Headers(await headers()),
        method,
        path,
        source,
        secret,
    );
}

export function rateLimitResponseHeaders(
    response: Response,
): Headers {
    const result = new Headers({
        "Cache-Control": "no-store",
    });

    const retryAfter = response.headers.get(
        "Retry-After",
    );

    if (retryAfter && /^\d+$/.test(retryAfter)) {
        result.set("Retry-After", retryAfter);
    }

    return result;
}