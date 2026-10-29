/** @jest-environment node */

import {
    rateLimitResponseHeaders,
    signedClientHeaders,
} from "../../src/lib/clientIpForwarding";

const SECRET =
    "test-proxy-secret-at-least-32-bytes-long";

test("uses the final address appended by the ALB", () => {
    const result = signedClientHeaders(
        new Headers({
            "x-forwarded-for": "1.2.3.4, 203.0.113.8",
            "x-penflow-client-ip": "8.8.8.8",
        }),
        "GET",
        "/limited/a",
        "alb",
        SECRET,
        1700000000,
    );

    expect(
        result.get("X-PenFlow-Client-IP"),
    ).toBe("203.0.113.8");

    expect(
        result.get("X-PenFlow-Client-Signature"),
    ).toBe(
        "1026b2f329480844fe81cc265bf893f27f95bdee7a28c2373beb895aeb74d816",
    );
});

test("local mode ignores incoming forwarded addresses", () => {
    const result = signedClientHeaders(
        new Headers({
            "x-forwarded-for": "8.8.8.8",
        }),
        "GET",
        "/limited/a",
        "local",
        SECRET,
    );

    expect(
        result.get("X-PenFlow-Client-IP"),
    ).toBe("127.0.0.1");
});

test("ALB mode requires a valid forwarded address", () => {
    expect(() => signedClientHeaders(
        new Headers(),
        "GET",
        "/limited/a",
        "alb",
        SECRET,
    )).toThrow();
});

test("preserves Retry-After through the proxy", () => {
    const result = rateLimitResponseHeaders(
        new Response(null, {
            status: 429,
            headers: {
                "Retry-After": "60",
            },
        }),
    );

    expect(result.get("Retry-After")).toBe("60");
    expect(result.get("Cache-Control")).toBe("no-store");
});