DATABASE_SIGNATURES = {
    "phpMyAdmin": {
        "category": "database",
        "vendor": "phpmyadmin",
        "product": "phpmyadmin",
        "cpe": "cpe:2.3:a:phpmyadmin:phpmyadmin",
        "cookies": [("phpmyadmin", "", 90)],
        "html": [("phpmyadmin", 50)],
        "version_extractors": []
    },
    "MySQL": {
        "category": "database",
        "vendor": "oracle",
        "product": "mysql",
        "cpe": "cpe:2.3:a:oracle:mysql",
        "html": [("you have an error in your sql syntax", 80)], # Basic error leak
        "version_extractors": []
    }
}