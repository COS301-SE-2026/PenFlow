/** @jest-environment node */

import { NextRequest } from "next/server";

import {
    buildContentSecurityPolicy,
    createNonce,
} from "@/lib/contentSecurityPolicy";
import { middleware } from "@/middleware";

const originalApp = process.env.APP_URL;
const originalKeycloak = process.env.KEYCLOAK_PUBLIC_URL;

const settings = {
    appUrl: "https://app.example.com",
    keycloakUrl: "https://auth.example.com",
    development: false,
};

afterEach(() => {
    if (originalApp === undefined) {
        delete process.env.APP_URL;
    } else {
        process.env.APP_URL = originalApp;
    }

    if (originalKeycloak === undefined) {
        delete process.env.KEYCLOAK_PUBLIC_URL;
    } else {
        process.env.KEYCLOAK_PUBLIC_URL = originalKeycloak;
    }
});

test("generates fresh 128-bit nonces", () => {
    const nonce = createNonce();

    expect(nonce).toMatch(/^[A-Za-z0-9+/]{22}==$/);
    expect(createNonce()).not.toBe(nonce);
});

test("production script policy requires a nonce", () => {
    const nonce = createNonce();

    const policy = buildContentSecurityPolicy({
        ...settings,
        nonce,
    });

    const scriptPolicy = policy
        .split("; ")
        .find((value) => value.startsWith("script-src "))!;

    expect(scriptPolicy).toContain(`'nonce-${nonce}'`);
    expect(scriptPolicy).toContain("'strict-dynamic'");
    expect(scriptPolicy).not.toContain("'unsafe-inline'");
    expect(scriptPolicy).not.toContain("'unsafe-eval'");

    expect(policy).toContain("connect-src 'self'");
    expect(policy).toContain(
        "form-action 'self' https://auth.example.com",
    );
    expect(policy).toContain("frame-ancestors 'none'");
    expect(policy).toContain("upgrade-insecure-requests");
});

test("development allows the configured HMR websocket", () => {
    const policy = buildContentSecurityPolicy({
        ...settings,
        nonce: createNonce(),
        appUrl: "http://localhost:3000",
        development: true,
    });

    expect(policy).toContain("'unsafe-eval'");
    expect(policy).toContain(
        "connect-src 'self' ws://localhost:3000",
    );
    expect(policy).not.toContain(
        "upgrade-insecure-requests",
    );
});

test("local production HTTP is not upgraded", () => {
    const policy = buildContentSecurityPolicy({
        ...settings,
        nonce: createNonce(),
        appUrl: "http://localhost:3000",
    });

    expect(policy).not.toContain(
        "upgrade-insecure-requests",
    );
});

test.each([
    "",
    "bad",
    "'injected;",
])("rejects malformed nonce %s", (nonce) => {
    expect(() =>
        buildContentSecurityPolicy({
            ...settings,
            nonce,
        }),
    ).toThrow();
});

test("replaces client nonce and forwards matching CSP", () => {
    process.env.APP_URL = settings.appUrl;
    process.env.KEYCLOAK_PUBLIC_URL = settings.keycloakUrl;

    const response = middleware(
        new NextRequest("http://internal:3000/", {
            headers: {
                "x-nonce": "attacker",
                "Content-Security-Policy": (
                    "script-src 'unsafe-inline'"
                ),
            },
        }),
    );

    const policy = response.headers.get(
        "Content-Security-Policy",
    )!;

    const nonce = response.headers.get(
        "x-middleware-request-x-nonce",
    )!;

    expect(nonce).toMatch(/^[A-Za-z0-9+/]{22}==$/);
    expect(nonce).not.toBe("attacker");
    expect(policy).toContain(`'nonce-${nonce}'`);

    expect(
        response.headers.get(
            "x-middleware-request-content-security-policy",
        ),
    ).toBe(policy);

    expect(
        response.headers.get("Cache-Control"),
    ).toBe("private, no-store");
});

test("retains CSRF blocking", () => {
    process.env.APP_URL = settings.appUrl;
    process.env.KEYCLOAK_PUBLIC_URL = settings.keycloakUrl;

    const response = middleware(
        new NextRequest(
            "http://internal:3000/api/findings",
            {
                method: "POST",
                headers: {
                    Origin: "https://evil.example",
                },
            },
        ),
    );

    expect(response.status).toBe(403);
});