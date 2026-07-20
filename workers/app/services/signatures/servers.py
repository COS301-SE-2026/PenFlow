SERVER_SIGNATURES = {
    "nginx": {
        "category": "web_server",
        "vendor": "f5",
        "product": "nginx",
        "headers": [
            ("server", "nginx", 80)
        ],
        "version_extractors": [
            {
                "type": "header",
                "target": "server",
                "regex": r"nginx/([\d\.]+)"
            }
        ]
    },
    "Google Web Server": {
        "category": "web_server",
        "vendor": "google",
        "product": "gws",
        "headers": [
            ("server", "gws", 100)
        ],
        "version_extractors": []
    },
    "Apache": {
        "category": "web_server",
        "vendor": "apache",
        "product": "http_server",
        "headers": [
            ("server", "apache", 80)
        ],
        "version_extractors": [
            {
                "type": "header",
                "target": "server",
                "regex": r"apache/([\d\.]+)"
            }
        ]
    },
    "Apache Tomcat": {
        "category": "web_server",
        "vendor": "apache",
        "product": "tomcat",
        "headers": [("server", "coyote", 90)],
        "version_extractors": [{"type": "header", "target": "server", "regex": r"coyote/([\d\.]+)"}]
    },
    "Cloudflare": {
        "category": "web_server",
        "vendor": "cloudflare",
        "product": "cloudflare",
        "headers": [
            ("server", "cloudflare", 90)
        ],
        "version_extractors": []
    },
}