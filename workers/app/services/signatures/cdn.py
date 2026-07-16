CDN_SIGNATURES = {
    "Cloudflare": {
        "category": "cdn",
        "vendor": "cloudflare",
        "product": "cloudflare",
        "cpe": "cpe:2.3:a:cloudflare:cloudflare",
        "headers": [
            ("cf-ray", "cloudflare", 90),
            ("cf-cache-status", "cloudflare", 80),
            ("server", "cloudflare", 90)
        ],
        "version_extractors": []
    },
    "Fastly": {
        "category": "cdn",
        "vendor": "fastly",
        "product": "fastly",
        "cpe": "cpe:2.3:a:fastly:fastly",
        "headers": [("fastly-client-ip", "fastly", 90)],
        "version_extractors": []
    }
}