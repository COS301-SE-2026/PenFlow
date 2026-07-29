LANGUAGE_SIGNATURES = {
    "PHP": {
        "category": "language",
        "vendor": "php",
        "product": "php",
        "headers": [("x-powered-by", "php", 70)],
        "cookies": [("phpsessid", "php", 90)],
        "version_extractors": [
            {"type": "header", "target": "x-powered-by", "regex": r"PHP/([\d\.]+)"}
        ],
    },
    "ASP.NET": {
        "category": "language",
        "vendor": "microsoft",
        "product": "asp.net",
        "headers": [("x-aspnet-version", "asp.net", 90)],
        "cookies": [("asp.net_sessionid", "asp.net", 90)],
        "version_extractors": [
            {"type": "header", "target": "x-aspnet-version", "regex": r"([\d\.]+)"}
        ],
    },
}
