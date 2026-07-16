SERVER_SIGNATURES = {
    "nginx": {
        "category": "web_server",
        "vendor": "f5",
        "product": "nginx",
        "cpe": "cpe:2.3:a:f5:nginx:{version}:*:*:*:*:*:*:*",
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
        "cpe": "cpe:2.3:a:google:{version}:*:*:*:*:*:*:*",
        "headers": [
            ("server", "gws", 100)
        ],
        "version_extractors": []
    },
    "Apache": {
        "category": "web_server",
        "vendor": "apache",
        "product": "http_server",
        "cpe": "cpe:2.3:a:apache:{version}:*:*:*:*:*:*:*",
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
    }
}