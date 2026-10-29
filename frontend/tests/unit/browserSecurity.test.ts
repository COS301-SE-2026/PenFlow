/** @jest-environment node */

import { NextRequest } from "next/server";

import {
    applicationOrigin,
    isAllowedBrowserRequest,
} from "@/lib/browserSecurity";
import { middleware } from "@/middleware";

const APP_ORIGIN = "https://app.example.com";
const originalAppUrl = process.env.APP_URL;

afterEach(() => {
    if (originalAppUrl === undefined) {
        delete process.env.APP_URL;
    } else {
        process.env.APP_URL = originalAppUrl;
    }
});

test.each(["POST", "PUT", "PATCH", "DELETE"])(
    "%s accepts the configured origin",
    (method) => {
        expect(
            isAllowedBrowserRequest(
                method,
                new Headers({ Origin: APP_ORIGIN }),
                APP_ORIGIN,
            ),
        ).toBe(true);
    },
);

test.each([
    "https://evil.example",
    "https://other.example.com",
    "https://app.example.com.evil.example",
    "http://app.example.com",
    "https://app.example.com:444",
    "null",
    "not a URL",
    "https://user@app.example.com",
    "https://app.example.com/path",
])("rejects invalid or unrelated origin %s", (origin) => {
    expect(
        isAllowedBrowserRequest(
            "POST",
            new Headers({ Origin: origin }),
            APP_ORIGIN,
        ),
    ).toBe(false);
});

test("rejects unverifiable mutations", () => {
    expect(
        isAllowedBrowserRequest(
            "POST",
            new Headers(),
            APP_ORIGIN,
        ),
    ).toBe(false);
});

test("allows a same-origin Referer fallback", () => {
    expect(
        isAllowedBrowserRequest(
            "POST",
            new Headers({
                Referer: `${APP_ORIGIN}/findings/1`,
            }),
            APP_ORIGIN,
        ),
    ).toBe(true);
});

test("invalid Origin cannot fall back to Referer", () => {
    expect(
        isAllowedBrowserRequest(
            "POST",
            new Headers({
                Origin: "null",
                Referer: `${APP_ORIGIN}/`,
            }),
            APP_ORIGIN,
        ),
    ).toBe(false);
});

test("rejects cross-site Fetch Metadata", () => {
    expect(
        isAllowedBrowserRequest(
            "POST",
            new Headers({
                Origin: APP_ORIGIN,
                "Sec-Fetch-Site": "cross-site",
            }),
            APP_ORIGIN,
        ),
    ).toBe(false);
});

test("allows OAuth GET navigation", () => {
    expect(
        isAllowedBrowserRequest(
            "GET",
            new Headers({
                Origin: "https://auth.example.com",
            }),
            APP_ORIGIN,
        ),
    ).toBe(true);
});

test("does not trust spoofed host headers", () => {
    expect(
        isAllowedBrowserRequest(
            "POST",
            new Headers({
                Origin: "https://evil.example",
                Host: "evil.example",
                "X-Forwarded-Host": "evil.example",
            }),
            APP_ORIGIN,
        ),
    ).toBe(false);
});

test("requires a configured origin in production", () => {
    expect(() => applicationOrigin("", true)).toThrow();
});

test("supports explicitly configured local HTTP", () => {
    expect(
        applicationOrigin("http://localhost:3000", true),
    ).toBe("http://localhost:3000");
});

test("handles HTTPS behind an internal HTTP proxy", () => {
    process.env.APP_URL = APP_ORIGIN;

    const response = middleware(
        new NextRequest(
            "http://internal:3000/api/findings",
            {
                method: "POST",
                headers: { Origin: APP_ORIGIN },
            },
        ),
    );

    expect(response.status).toBe(200);
    expect(
        response.headers.get("Strict-Transport-Security"),
    ).toBe("max-age=31536000");
    expect(
        response.headers.get("Cache-Control"),
    ).toBe("no-store");
});

test("middleware blocks unrelated origins", () => {
    process.env.APP_URL = APP_ORIGIN;

    const response = middleware(
        new NextRequest(
            "http://internal:3000/api/findings",
            {
                method: "POST",
                headers: { Origin: "https://evil.example" },
            },
        ),
    );

    expect(response.status).toBe(403);
});

test("local HTTP does not receive HSTS", () => {
    process.env.APP_URL = "http://localhost:3000";

    const response = middleware(
        new NextRequest("http://localhost:3000/"),
    );

    expect(
        response.headers.get("Strict-Transport-Security"),
    ).toBeNull();
});