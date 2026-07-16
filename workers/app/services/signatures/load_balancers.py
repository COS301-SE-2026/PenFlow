LOAD_BALANCER_SIGNATURES = {
    "HAProxy": {
        "category": "load_balancer",
        "vendor": "haproxy",
        "product": "haproxy",
        "cpe": "cpe:2.3:a:haproxy:haproxy",
        "cookies": [("haproxy", "",90)],
        "headers": [("via", "haproxy", 80)],
        "version_extractors": []
    },
    "AWS ELB": {
        "category": "load_balancer",
        "vendor": "amazon",
        "product": "elastic_load_balancing",
        "cpe": "cpe:2.3:a:amazon:elastic_load_balancing",
        "cookies": [("awselb", "", 100)],
        "headers": [("x-amz-cf-id", "amazon", 80)],
        "version_extractors": []
    },
    "F5 BIG-IP": {
        "category": "load_balancer",
        "vendor": "f5",
        "product": "big-ip",
        "cpe": "cpe:2.3:a:f5:big-ip",
        "cookies": [("bigipserver", "",100)],
        "headers": [("x-cnection", "close", 40)],
        "version_extractors": []
    }
}