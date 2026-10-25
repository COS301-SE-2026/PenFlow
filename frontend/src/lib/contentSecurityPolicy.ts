import { applicationOrigin } from "@/lib/browserSecurity";

export function createNonce(): string {
    const bytes = crypto.getRandomValues(new Uint8Array(16));

    return btoa(String.fromCharCode(...bytes));
}

export function buildContentSecurityPolicy({
    nonce,
    appUrl,
    keycloakUrl,
    development,
}: {
    nonce: string;
    appUrl: string;
    keycloakUrl: string;
    development: boolean;
}): string {
    if (!/^[A-Za-z0-9+/]{22}==$/.test(nonce)) {
        throw new Error("Invalid CSP nonce");
    }

    const appOrigin = applicationOrigin(appUrl);
    const keycloakOrigin = applicationOrigin(keycloakUrl);

    const connectSources = ["'self'"];

    if (development) {
        const websocket = new URL(appOrigin);

        websocket.protocol = (
            websocket.protocol === "https:"
                ? "wss:"
                : "ws:"
        );

        connectSources.push(websocket.origin);
    }

    const directives = [
        "default-src 'self'",
        (
            `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`
            + (development ? " 'unsafe-eval'" : "")
        ),
        "script-src-attr 'none'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' blob: data:",
        "font-src 'self'",
        `connect-src ${connectSources.join(" ")}`,
        "object-src 'none'",
        "base-uri 'none'",
        `form-action 'self' ${keycloakOrigin}`,
        "frame-src 'none'",
        "frame-ancestors 'none'",
    ];

    if (
        !development
        && appOrigin.startsWith("https://")
    ) {
        directives.push("upgrade-insecure-requests");
    }

    return directives.join("; ");
}