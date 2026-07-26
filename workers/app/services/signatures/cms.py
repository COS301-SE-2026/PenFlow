CMS_SIGNATURES = {
    "WordPress": {
        "category": "cms",
        "vendor": "wordpress",
        "product": "wordpress",
        "meta": [("wordpress", 60)],
        "scripts": [("wp-content", 20), ("wp-includes", 20)],
        "headers": [("link", 10)],
        "version_extractors": [
            {"type": "meta", "target": "generator", "regex": r"WordPress\s+([\d\.]+)"}
        ],
    },
    "Drupal": {
        "category": "cms",
        "vendor": "drupal",
        "product": "drupal",
        "meta": [("drupal", 70)],
        "scripts": [("drupal.js", 30)],
        "headers": [("x-generator", 50)],
        "version_extractors": [
            {"type": "header", "target": "x-generator", "regex": r"Drupal\s+([\d\.]+)"},
            {"type": "meta", "target": "generator", "regex": r"Drupal\s+([\d\.]+)"},
        ],
    },
}
