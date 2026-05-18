"""
Have I Been Pwned (HIBP) API v3 — Local Mock Server
====================================================
Mimics the real HIBP API at https://haveibeenpwned.com/api/v3
Run with:  python app.py
Base URL:  http://localhost:5000/api/v3

Endpoints implemented
─────────────────────
Auth required (pass any value in hibp-api-key header):
  GET /api/v3/breachedaccount/{email}          ?truncateResponse=false&includeUnverified=true
  GET /api/v3/pasteaccount/{email}
  GET /api/v3/breacheddomain/{domain}
  GET /api/v3/stealerlogsbyemail/{email}       (Pwned 5+ tier)
  GET /api/v3/stealerlogsbydomain/{domain}     (Pwned 5+ tier)
  GET /api/v3/subscriptions/domains
  GET /api/v3/subscriptions

No auth required:
  GET /api/v3/breaches                         ?domain=example.com
  GET /api/v3/breach/{name}
  GET /api/v3/latestbreach
  GET /api/v3/dataclasses

Pwned Passwords (separate base, no auth, k-anonymity):
  GET /range/{prefix}    (5-char SHA-1 hex prefix)
"""

import hashlib
import re
from flask import Flask, request, jsonify, Response, abort

app = Flask(__name__)

# ── Fake API key ──────────────────────────────────────────────────────────────
VALID_API_KEY = "REDACTED"

# ── Fake data store ───────────────────────────────────────────────────────────

BREACHES = [
    {
        "Name": "Adobe",
        "Title": "Adobe",
        "Domain": "adobe.com",
        "BreachDate": "2013-10-04",
        "AddedDate": "2013-12-04T00:00:00Z",
        "ModifiedDate": "2022-05-15T23:52:49Z",
        "PwnCount": 152445165,
        "Description": "In October 2013, 153 million Adobe accounts were breached.",
        "LogoPath": "https://haveibeenpwned.com/Content/Images/PwnedLogos/Adobe.png",
        "DataClasses": ["Email addresses", "Password hints", "Passwords", "Usernames"],
        "IsVerified": True,
        "IsFabricated": False,
        "IsSensitive": False,
        "IsRetired": False,
        "IsSpamList": False,
        "IsMalware": False,
        "IsSubscriptionFree": False,
    },
    {
        "Name": "LinkedIn",
        "Title": "LinkedIn",
        "Domain": "linkedin.com",
        "BreachDate": "2016-05-05",
        "AddedDate": "2016-05-22T21:25:10Z",
        "ModifiedDate": "2022-05-15T23:52:49Z",
        "PwnCount": 164611595,
        "Description": "In May 2016, LinkedIn had 164 million email addresses and passwords exposed.",
        "LogoPath": "https://haveibeenpwned.com/Content/Images/PwnedLogos/LinkedIn.png",
        "DataClasses": ["Email addresses", "Passwords"],
        "IsVerified": True,
        "IsFabricated": False,
        "IsSensitive": False,
        "IsRetired": False,
        "IsSpamList": False,
        "IsMalware": False,
        "IsSubscriptionFree": False,
    },
    {
        "Name": "Dropbox",
        "Title": "Dropbox",
        "Domain": "dropbox.com",
        "BreachDate": "2012-07-01",
        "AddedDate": "2016-08-31T00:13:19Z",
        "ModifiedDate": "2022-05-15T23:52:49Z",
        "PwnCount": 68648009,
        "Description": "In mid-2012, Dropbox suffered a data breach which exposed 68 million customers.",
        "LogoPath": "https://haveibeenpwned.com/Content/Images/PwnedLogos/Dropbox.png",
        "DataClasses": ["Email addresses", "Passwords"],
        "IsVerified": True,
        "IsFabricated": False,
        "IsSensitive": False,
        "IsRetired": False,
        "IsSpamList": False,
        "IsMalware": False,
        "IsSubscriptionFree": False,
    },
    {
        "Name": "MySpace",
        "Title": "MySpace",
        "Domain": "myspace.com",
        "BreachDate": "2008-07-01",
        "AddedDate": "2016-05-31T00:00:00Z",
        "ModifiedDate": "2022-05-15T23:52:49Z",
        "PwnCount": 359420698,
        "Description": "In approximately 2008, MySpace suffered a data breach that exposed almost 360 million accounts.",
        "LogoPath": "https://haveibeenpwned.com/Content/Images/PwnedLogos/MySpace.png",
        "DataClasses": ["Email addresses", "Passwords", "Usernames"],
        "IsVerified": True,
        "IsFabricated": False,
        "IsSensitive": False,
        "IsRetired": False,
        "IsSpamList": False,
        "IsMalware": False,
        "IsSubscriptionFree": False,
    },
    {
        "Name": "HaveIBeenPwned-Test",
        "Title": "HIBP Test Breach",
        "Domain": "hibp-integration-tests.com",
        "BreachDate": "2024-01-01",
        "AddedDate": "2024-01-15T00:00:00Z",
        "ModifiedDate": "2024-01-15T00:00:00Z",
        "PwnCount": 1000,
        "Description": "A fabricated breach used for testing HIBP integrations.",
        "LogoPath": "https://haveibeenpwned.com/Content/Images/PwnedLogos/HIBP.png",
        "DataClasses": ["Email addresses", "Passwords", "Phone numbers"],
        "IsVerified": True,
        "IsFabricated": True,
        "IsSensitive": False,
        "IsRetired": False,
        "IsSpamList": False,
        "IsMalware": False,
        "IsSubscriptionFree": True,
    },
    {
        "Name": "SpamList2024",
        "Title": "Spam List 2024",
        "Domain": "",
        "BreachDate": "2024-03-01",
        "AddedDate": "2024-03-10T00:00:00Z",
        "ModifiedDate": "2024-03-10T00:00:00Z",
        "PwnCount": 5000000,
        "Description": "A list of email addresses used for spam campaigns.",
        "LogoPath": "",
        "DataClasses": ["Email addresses"],
        "IsVerified": False,
        "IsFabricated": False,
        "IsSensitive": False,
        "IsRetired": False,
        "IsSpamList": True,
        "IsMalware": False,
        "IsSubscriptionFree": False,
    },
]

PASTES = [
    {
        "Source": "Pastebin",
        "Id": "8Q0BvKD8",
        "Title": "syslog",
        "Date": "2014-03-04T19:14:54Z",
        "EmailCount": 139,
    },
    {
        "Source": "Pastie",
        "Id": "7152479",
        "Title": None,
        "Date": "2013-03-28T16:51:10Z",
        "EmailCount": 30,
    },
    {
        "Source": "Slexy",
        "Id": "j5bAk0OV",
        "Title": None,
        "Date": "2020-11-28T12:00:00Z",
        "EmailCount": 4567,
    },
]

DATA_CLASSES = [
    "Account balances",
    "Age groups",
    "Auth tokens",
    "Avatars",
    "Bios",
    "Browser user agent details",
    "Dates of birth",
    "Device information",
    "Email addresses",
    "Employers",
    "Genders",
    "Geographic locations",
    "Government issued IDs",
    "IP addresses",
    "Names",
    "Passwords",
    "Payment histories",
    "Phone numbers",
    "Physical addresses",
    "Purchases",
    "Salutations",
    "Social connections",
    "Usernames",
    "Website activity",
]

# Deterministic mapping: email → which breaches they appear in
# Real API is deterministic per address; we replicate that with simple rules.
EMAIL_BREACH_MAP = {
    "account-exists@hibp-integration-tests.com": ["Adobe", "LinkedIn", "HaveIBeenPwned-Test"],
    "spam-list-only@hibp-integration-tests.com": ["SpamList2024"],
    "stealer-log@hibp-integration-tests.com": ["Dropbox", "HaveIBeenPwned-Test"],
    "multiple-breaches@example.com": ["Adobe", "LinkedIn", "Dropbox", "MySpace"],
    "no-breaches@example.com": [],
    "pwned@example.com": ["Adobe", "LinkedIn"],
}

EMAIL_PASTE_MAP = {
    "account-exists@hibp-integration-tests.com": PASTES,
    "stealer-log@hibp-integration-tests.com": [PASTES[0]],
    "multiple-breaches@example.com": PASTES,
    "pwned@example.com": [PASTES[0], PASTES[1]],
}

EMAIL_STEALER_MAP = {
    "stealer-log@hibp-integration-tests.com": ["google.com", "facebook.com", "twitter.com"],
    "account-exists@hibp-integration-tests.com": ["amazon.com"],
}

DOMAIN_BREACH_MAP = {
    "adobe.com": {"account1@adobe.com": ["Adobe"], "account2@adobe.com": ["Adobe", "LinkedIn"]},
    "example.com": {
        "pwned@example.com": ["Adobe", "LinkedIn"],
        "multiple-breaches@example.com": ["Adobe", "LinkedIn", "Dropbox", "MySpace"],
    },
    "hibp-integration-tests.com": {
        "account-exists@hibp-integration-tests.com": ["Adobe", "LinkedIn", "HaveIBeenPwned-Test"],
        "stealer-log@hibp-integration-tests.com": ["Dropbox", "HaveIBeenPwned-Test"],
    },
}

STEALER_DOMAIN_MAP = {
    "google.com": ["stealer-log@hibp-integration-tests.com", "user@example.com"],
    "facebook.com": ["stealer-log@hibp-integration-tests.com"],
}

SUBSCRIBED_DOMAINS = [
    {
        "DomainName": "example.com",
        "PwnCount": 15230,
        "PwnCountExcludingSpamLists": 14981,
        "NextSubscriptionRenewal": "2026-01-01T00:00:00Z",
        "CurrentSubscriptionDomain": True,
    },
    {
        "DomainName": "hibp-integration-tests.com",
        "PwnCount": 42,
        "PwnCountExcludingSpamLists": 42,
        "NextSubscriptionRenewal": "2026-01-01T00:00:00Z",
        "CurrentSubscriptionDomain": True,
    },
]

# Pwned Passwords: sha1(password).upper() → count
# Seeded with well-known weak passwords
PWNED_PASSWORDS = {
    hashlib.sha1(pw.encode()).hexdigest().upper(): count
    for pw, count in [
        ("password",     9659365),
        ("password123",  2323928),
        ("123456",       24230577),
        ("qwerty",       3993346),
        ("letmein",      1246129),
        ("monkey",       980209),
        ("dragon",       981837),
        ("abc123",       2869336),
        ("iloveyou",     1418296),
        ("admin",        2150896),
        ("welcome",      1021510),
        ("login",        402193),
        ("hello",        294835),
        ("sunshine",     461443),
        ("shadow",       716000),
        ("master",       495823),
        ("passw0rd",     842167),
        ("Password1",    2198977),
        ("p@ssword",     400291),
        ("trustno1",     1028671),
    ]
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def require_api_key():
    key = request.headers.get("hibp-api-key") or request.headers.get("Hibp-Api-Key")
    if not key:
        abort(401, description="Unauthorised — no API key supplied")
    # Accept the real sentinel and our test key alike; reject obvious blanks
    if key.strip() == "":
        abort(401, description="Unauthorised — blank API key")


def email_in_db(email: str) -> bool:
    return email.lower() in EMAIL_BREACH_MAP


def breaches_for_email(email: str, truncate: bool, include_unverified: bool):
    key = email.lower()
    breach_names = EMAIL_BREACH_MAP.get(key)
    if breach_names is None:
        # Unknown address: deterministically assign based on hash so behaviour is stable
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        all_names = [b["Name"] for b in BREACHES if not b["IsSpamList"]]
        breach_names = [all_names[i] for i in range(len(all_names)) if h & (1 << i)]
        if not breach_names:
            return None  # 404

    result = [b for b in BREACHES if b["Name"] in breach_names]
    if not include_unverified:
        result = [b for b in result if b["IsVerified"]]

    if truncate:
        return [{"Name": b["Name"]} for b in result]
    return result


def _not_found():
    return Response(status=404)


def _unauthorised(msg="Unauthorised"):
    return jsonify({"statusCode": 401, "message": msg}), 401


def _bad_request(msg):
    return jsonify({"statusCode": 400, "message": msg}), 400


# ── Auth-required endpoints ───────────────────────────────────────────────────

@app.route("/api/v3/breachedaccount/<path:email>")
def breached_account(email):
    require_api_key()
    email = email.lower().strip()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return _bad_request("The value entered is not a valid email address")

    truncate = request.args.get("truncateResponse", "true").lower() != "false"
    include_unverified = request.args.get("includeUnverified", "false").lower() == "true"

    result = breaches_for_email(email, truncate, include_unverified)
    if result is None or len(result) == 0:
        return _not_found()
    return jsonify(result)


@app.route("/api/v3/pasteaccount/<path:email>")
def paste_account(email):
    require_api_key()
    email = email.lower().strip()
    pastes = EMAIL_PASTE_MAP.get(email)
    if not pastes:
        # Deterministically assign for unknown addresses
        h = int(hashlib.md5(email.encode()).hexdigest(), 16)
        if h % 3 == 0:
            pastes = PASTES[:2]
        else:
            return _not_found()
    return jsonify(pastes)


@app.route("/api/v3/breacheddomain/<domain>")
def breached_domain(domain):
    require_api_key()
    domain = domain.lower()
    data = DOMAIN_BREACH_MAP.get(domain)
    if not data:
        return _not_found()
    return jsonify(data)


@app.route("/api/v3/stealerlogsbyemail/<path:email>")
def stealer_logs_by_email(email):
    require_api_key()
    email = email.lower()
    domains = EMAIL_STEALER_MAP.get(email)
    if not domains:
        return _not_found()
    return jsonify(sorted(domains))


@app.route("/api/v3/stealerlogsbydomain/<domain>")
def stealer_logs_by_domain(domain):
    require_api_key()
    domain = domain.lower()
    emails = STEALER_DOMAIN_MAP.get(domain)
    if not emails:
        return _not_found()
    return jsonify(sorted(emails))


@app.route("/api/v3/subscriptions/domains")
def subscribed_domains():
    require_api_key()
    return jsonify(SUBSCRIBED_DOMAINS)


@app.route("/api/v3/subscription")
def subscription():
    require_api_key()
    return jsonify({
        "SubscriptionName": "Pwned 3",
        "Description": "Access to all HIBP APIs for individual email lookups",
        "MonthlyQuota": 1000,
        "RequestsThisMonth": 42,
        "DailyQuota": 100,
        "RequestsToday": 7,
        "Rpm": 10,
    })


# ── No-auth endpoints ─────────────────────────────────────────────────────────

@app.route("/api/v3/breaches")
def all_breaches():
    domain_filter = request.args.get("domain", "").lower()
    result = BREACHES
    if domain_filter:
        result = [b for b in result if b.get("Domain", "").lower() == domain_filter]
    return jsonify(result)


@app.route("/api/v3/breach/<name>")
def single_breach(name):
    breach = next((b for b in BREACHES if b["Name"].lower() == name.lower()), None)
    if not breach:
        return _not_found()
    return jsonify(breach)


@app.route("/api/v3/latestbreach")
def latest_breach():
    latest = max(BREACHES, key=lambda b: b["AddedDate"])
    return jsonify(latest)


@app.route("/api/v3/dataclasses")
def data_classes():
    return jsonify(DATA_CLASSES)


# ── Pwned Passwords (k-anonymity, separate conceptual base) ───────────────────
# Real base URL is https://api.pwnedpasswords.com/range/{prefix}
# We expose it here at /range/{prefix} for local dev convenience.

@app.route("/range/<prefix>")
def pwned_passwords_range(prefix):
    if len(prefix) != 5 or not re.match(r"^[0-9A-Fa-f]{5}$", prefix):
        return Response("The hash prefix was not in a valid format", status=400)

    prefix = prefix.upper()
    lines = []
    for sha1, count in PWNED_PASSWORDS.items():
        if sha1.startswith(prefix):
            suffix = sha1[5:]
            lines.append(f"{suffix}:{count}")

    # Add some noise hashes so the response looks realistic regardless of prefix
    noise_hashes = [
        "A1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0",
        "B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0C1",
        "C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0C1D2",
        "D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0C1D2E3",
        "E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0C1D2E3F4",
    ]
    for h in noise_hashes:
        if h.startswith(prefix) and h not in PWNED_PASSWORDS:
            lines.append(f"{h[5:]}:1")

    return Response("\r\n".join(lines), mimetype="text/plain")


# ── Index / health ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return jsonify({
        "service": "HIBP Mock API v3",
        "status": "ok",
        "note": "This is a local mock server for development — NOT real HIBP data.",
        "endpoints": [
            "GET /api/v3/breachedaccount/{email}  (auth)",
            "GET /api/v3/pasteaccount/{email}      (auth)",
            "GET /api/v3/breacheddomain/{domain}   (auth)",
            "GET /api/v3/stealerlogsbyemail/{email}(auth)",
            "GET /api/v3/stealerlogsbydomain/{domain}(auth)",
            "GET /api/v3/subscriptions/domains     (auth)",
            "GET /api/v3/subscription              (auth)",
            "GET /api/v3/breaches",
            "GET /api/v3/breach/{name}",
            "GET /api/v3/latestbreach",
            "GET /api/v3/dataclasses",
            "GET /range/{5-char-sha1-prefix}       (Pwned Passwords)",
        ],
        "test_api_key": VALID_API_KEY,
        "test_emails": list(EMAIL_BREACH_MAP.keys()),
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  HIBP Mock Server running at http://localhost:5000")
    print(f"  Test API key: {VALID_API_KEY}")
    print("=" * 60)
    app.run(debug=True, port=5000)
