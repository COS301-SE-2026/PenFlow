# Phase 2 Data Flow

## Overview

This document describes how information moves through the Phase 2 scanning architecture.

---

# High-Level Data Flow

```
High-Level Data Flow

User

Backend API

Create Scan Record

Target Resolution

Nmap

    - TLS Worker
    - HTTP Security Worker
    - Fingerprinting Worker
    - CPE Resolver Worker
    - CVE Worker

Backend Callback

Database

Frontend
```

The data becomes more structured as it moves through the system.

---

# Step 1 — Scan Creation

The process begins when a user requests a new scan through the frontend.
The backend validates the request before creating a new scan task.

At this stage the scan only contains metadata such as:

- **Scan ID**
- **Target**
- **Owner**
- **Scan status**

The Scan ID becomes the unique identifier used throughout the entire pipeline.

---

# Step 2 — Queue Dispatch

Rather than executing immediately, the scan request is placed onto the Celery task queue.
This allows us to keep the UI and backend responsive while we handle requests.

At this point the scan data consists primarily of:

- Scan identifier
- Target information
- Initial scan status

---

# Step 3 — Worker Processing

Each worker receives the information required for its specific responsibility.

Examples include:

- Target Resolution produces IP addresses.
- Nmap discovers open ports.
- HTTP Security analyses security headers.
- TLS inspects certificates.
- Fingerprinting identifies technologies.
- CPE Resolver produces CPE identifiers.
- CVE searches vulnerability databases.

Every worker returns information using the standard data contract we have established.

```json
{
    "raw_result": {},
    "findings": [],
    "assets": [],
    "status": "completed"
}
```

Although the raw scan data differs between workers, the returned structure remains consistent.

---

# Step 4 — Data Normalisation

Once worker execution completes, the returned information is transformed into the project's common data model.

The architecture separates information into three categories.

| Data | Purpose |
|-------|----------|
| Raw Result | Original worker output retained for traceability and debugging |
| Findings | Security observations identified during scanning |
| Assets | Infrastructure, services and technologies discovered during scanning |

Because every worker eventually produces Findings and Assets, the reporting layer and frontend no longer need to understand worker-specific JSON, much like what we had initially set up in phase 1(demo 1)

---

# Step 5 — Persistence

The normalised data is written into the database.

Current Phase 2 stores information primarily within:

- Scan
- Finding
- Asset

This allows later components to retrieve structured information directly instead of repeatedly processing raw worker output.

---

# Step 6 — Backend Filtering

When the frontend requests information, it does not retrieve raw worker output.

Instead it queries dedicated backend endpoints such as:

- Findings
- Assets
- Services (future)

Filtering, searching, sorting and pagination are performed inside the backend repositories before data is returned.

---

# Step 7 — Frontend Presentation

After filtering has completed, the backend returns only the requested information.
The frontend is therefore responsible only for displaying data rather than interpreting worker results. Keeping it light and as responsive as we could make it.

---

# Data Transformation Summary

The following section summarises how the information changes throughout the pipeline.

```
Scan Request

Target Information

Worker Raw Results

Normalised Findings & Assets

Database Records

Filtered API Responses

Frontend Display
```

Each stage increases the structure and usability of the information while reducing the amount of worker-specific knowledge required by downstream components.

---