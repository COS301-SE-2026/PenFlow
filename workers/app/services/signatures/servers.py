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
    }
}