const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

function parsedOrigin(
    value: string,
    originOnly: boolean,
): string | null {
    if (value !== value.trim()) return null;

    try {
        const url = new URL(value);

        if (
            !["http:", "https:"].includes(url.protocol)
            || url.username
            || url.password
            || (
                originOnly
                && (
                    url.pathname !== "/"
                    || url.search
                    || url.hash
                )
            )
        ) {
            return null;
        }

        return url.origin;
    } catch {
        return null;
    }
}

export function applicationOrigin(
    configured: string | undefined = process.env.APP_URL,
    production = process.env.NODE_ENV === "production",
): string {
    const value = configured
        ?? (production ? "" : "http://localhost:3000");

    const origin = parsedOrigin(value, true);

    if (!origin) {
        throw new Error(
            "APP_URL must be a valid application origin",
        );
    }

    return origin;
}

export function isAllowedBrowserRequest(
    method: string,
    headers: Headers,
    expectedOrigin: string,
): boolean {
    if (SAFE_METHODS.has(method.toUpperCase())) return true;

    if (headers.get("sec-fetch-site") === "cross-site") {
        return false;
    }

    const origin = headers.get("origin");

    if (origin !== null) {
        return parsedOrigin(origin, true) === expectedOrigin;
    }

    const referer = headers.get("referer");

    return (
        referer !== null
        && parsedOrigin(referer, false) === expectedOrigin
    );
}