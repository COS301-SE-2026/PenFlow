# OSINT Worker API Documentation

## Overview
This document shows the data structures returned by the PenFlow OSINT workers. All workers normalize their raw external API outputs into a unified JSON format to ensure database consistency.

## Unified Data Schema
The `data_contract_schema.json` acts as the strict contract between the OSINT Python workers and the main Backend API. 

### Key Database Type Mappings

**`Metadata`**
* `scan_id`: UUID (Primary Key)
* `target_domain`: VARCHAR / TEXT
* `scan_timestamp`: TIMESTAMP
* `status`: VARCHAR (eg: 'pending'; 'completed')

**`Infrastructure` (Shodan)**
* `hosting_provider`: TEXT
* `ip_str`: VARCHAR / TEXT (192.168.1.1)
* `ip_int`: BIGINT (For high-speed database indexing and range queries: 1745904436)
* `port`: INTEGER
* `state`: VARCHAR (eg: 'open'; 'closed')

**`Tech Stack` (Wappalyzer)**
* `name`: VARCHAR / TEXT
* `version`: VARCHAR / TEXT *(Critical: Must be a string because the worker will return the string "Unknown" if the developers successfully hid their versions).*

**`Subdomains` (crt.sh)**
* `total_found`: INTEGER
* `discovered_names`: TEXT[] (Array of strings)

**`Reputation` (URLScan)**
* `malicious_flags`: INTEGER
* `urlscan_uuid`: VARCHAR
* `screenshot_url`: TEXT (Stores the URL to be downloaded for the PDF report)

**`Phishing Surface` (Hunter.io)**
* `email_format_pattern`: VARCHAR
* `email`: VARCHAR / TEXT
* `type`: VARCHAR (eg: 'personal'; 'generic')
* `confidence_score`: INTEGER

**`Breach Data` (HaveIBeenPwned)**
* `pwned_accounts_count`: INTEGER
* `known_breaches`: TEXT[] (Array of strings, eg: ["LinkedIn"; "Adobe"])

## Raw Response Notes
Raw API responses are stored in `/workers/docs/raw_samples` for local testing without wasting API credits.

## Data Transformation Example (Shodan)

To illustrate the normalization logic, here is a comparison between the raw provider response and the unified PenFlow format.

### Before: Raw Shodan JSON (Abbreviated)
This is a snippet of the ~10,000 line "messy" response the worker receives:
```json
{
  "org": "Cloudflare, Inc.",
  "ip_str": "104.16.99.52",
  "ports": [80, 443, 8080],
  "data": [
    { "port": 80, "hash": -1785004229, "location": "/" },
    { "port": 443, "hash": 958142897, "location": "/" }
  ]
}
```

### After: PenFlow Unified Format

This is an example of how the worker extracts and cleans the data into our predictable structure for the database:

```json
{
  "infrastructure": {
    "provider": "Shodan",
    "hosting_provider": "Cloudflare, Inc.",
    "ip_details": [
      {
        "ip_str": "104.16.99.52",
        "ip_int": 1745904436
      }
    ],
    "open_ports": [
      { "port": 80, "state": "open" },
      { "port": 443, "state": "open" }
    ]
  }
}
```


