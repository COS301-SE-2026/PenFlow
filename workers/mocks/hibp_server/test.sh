BASE=http://localhost:5000
KEY=REDACTED

# Breached account (truncated — default)
curl -s -H "hibp-api-key: $KEY" "$BASE/api/v3/breachedaccount/account-exists@hibp-integration-tests.com" | python3 -m json.tool

# Breached account (full response)
curl -s -H "hibp-api-key: $KEY" "$BASE/api/v3/breachedaccount/pwned@example.com?truncateResponse=false" | python3 -m json.tool

# No breaches → 404
curl -v -H "hibp-api-key: $KEY" "$BASE/api/v3/breachedaccount/no-breaches@example.com"

# Pastes
curl -s -H "hibp-api-key: $KEY" "$BASE/api/v3/pasteaccount/account-exists@hibp-integration-tests.com" | python3 -m json.tool

# All breaches
curl -s "$BASE/api/v3/breaches" | python3 -m json.tool

# Single breach
curl -s "$BASE/api/v3/breach/Adobe" | python3 -m json.tool

# Latest breach
curl -s "$BASE/api/v3/latestbreach" | python3 -m json.tool

# Data classes
curl -s "$BASE/api/v3/dataclasses" | python3 -m json.tool

# Pwned Passwords (k-anonymity) — SHA-1 of "password" starts with 5BAA6
curl -s "$BASE/range/5BAA6"

# No API key → 401
curl -v "$BASE/api/v3/breachedaccount/test@test.com"
