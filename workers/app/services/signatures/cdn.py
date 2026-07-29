CDN_SIGNATURES = {
    "Cloudflare": {
        "category": "cdn",
        "vendor": "cloudflare",
        "product": "cloudflare",
        "headers": [
            ("cf-ray", "cloudflare", 90),
            ("cf-cache-status", "cloudflare", 80),
            ("server", "cloudflare", 90),
        ],
        "version_extractors": [],
    },
    "Fastly": {
        "category": "cdn",
        "vendor": "fastly",
        "product": "fastly",
        "headers": [("fastly-client-ip", "fastly", 90)],
        "version_extractors": [],
    },
}
