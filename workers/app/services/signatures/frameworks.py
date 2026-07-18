FRAMEWORK_SIGNATURES = {
    "React": {
        "category": "framework",
        "vendor": "facebook",
        "product": "react",
        "html": [("data-reactroot", 80)],
        "scripts": [("react.production.min.js", 90)],
        "version_extractors": []
    },
    "NextJS": {
        "category": "framework",
        "vendor": "vercel",
        "product": "next.js",
        "html": [("__NEXT_DATA__", 90), ("_next/", 40)],
        "version_extractors": []
    }
}