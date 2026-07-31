# Software Requirements Specification (SRS)

# PenFlow
## Team: The BroCode

## Functional Requirement


#### FR-1: Initiate CTEM Scan
* **FR-1.1:** The system shall allow any user (authenticated or anonymous) to submit a domain name for OSINT scanning without requiring account creation.
* **FR-1.2:** The system shall validate the submitted domain name format before accepting the scan request.
* **FR-1.3:** The system shall generate and return a unique `scan_id` upon successful scan submission.
* **FR-1.4:** The system shall return an initial scan status (e.g., queued, in_progress) upon submission.
* **FR-1.5:** The system shall display real-time scan progress inline on the landing page, updating without requiring a page reload.
* **FR-1.6:** The system shall implement IP-based rate limiting to prevent abuse (maximum 3 scans per IP per 10 minutes).
* **FR-1.7:** The system shall complete gracefully even if one or more OSINT data sources are unavailable, returning partial results where possible.
* **FR-1.8:** The system shall allow any user (authenticated or anonymous) to optionally provide an email address at the time of scan initiation, to receive the comprehensive scan report upon completion.

#### FR-2: View Scan Report
* **FR-2.1:** The system shall allow any user (authenticated or anonymous) to view a scan report using a valid `scan_id`.
* **FR-2.2:** The system shall display all findings associated with the scan, including asset information and risk indicators.
* **FR-2.3:** The system shall display a basic risk overview summarising the overall security posture of the scanned domain.
* **FR-2.4:** The system shall generate a publicly accessible URL for each scan report using its unique `scan_id`, accessible without authentication.
* **FR-2.5:** The system shall clearly indicate the scan status (e.g., in_progress, complete, failed) on the report view.
* **FR-2.6:** The system shall display the timestamp of when the scan was completed.
* **FR-2.7:** The system shall display a brief inline summary of scan findings directly on the results page, accessible to any user (authenticated or anonymous) without requiring a download or account creation.
* **FR-2.8:** The system shall deliver the comprehensive scan report via email to any user who provided an email address at scan initiation; authenticated users shall additionally be able to access and download the detailed report directly from the platform.

#### FR-3: Scan History
* **FR-3.1:** The system shall allow authenticated users to view a list of all scans they have previously initiated.
* **FR-3.2:** The system shall display the following information for each historical scan: `scan_id`, domain, status, and `created_at` timestamp.
* **FR-3.3:** The system shall restrict scan history access to the authenticated user who initiated the scans — users shall not be able to view other users' scan history.
* **FR-3.4:** The system shall display scan history in reverse chronological order (most recent first).
* **FR-3.5:** The system shall allow the user to navigate from a scan history entry directly to the corresponding scan report.
* **FR-3.6:** The system shall display scan history across both Phase 1 (CTEM) and
  Phase 2 (vulnerability) scans, with the scan type clearly indicated for each entry.
* **FR-3.7:** The system shall allow the user to filter scan history by scan type
  (Phase 1 / Phase 2) and by asset.

#### FR-4: User Authentication
* **FR-4.1:** The system shall allow users to register using an email address and password.
* **FR-4.2:** The system shall enforce password strength validation during registration. A valid password must be a minimum of 8 characters and contain at least one uppercase letter, one lowercase letter, one digit, and one special character.
* **FR-4.3:** The system shall allow registered users to log in and receive a signed JWT access token, which must be included in subsequent authenticated requests.
* **FR-4.4:** The system shall associate scans initiated while authenticated with the user's account.
* **FR-4.5:** The system shall allow unauthenticated users to initiate scans and view reports, with scan history only accessible after login.

#### FR-5: OSINT Data Collection
* **FR-5.1:** The system shall perform DNS record lookups on the submitted domain, including MX, TXT, SPF, and DMARC records.
* **FR-5.2:** The system shall enumerate subdomains associated with the submitted domain using certificate transparency logs (crt.sh).
* **FR-5.3:** The system shall check email addresses discovered during the scan against known data breach databases (HaveIBeenPwned) to identify credential exposures linked to the target domain.
* **FR-5.4:** The system shall perform a passive Shodan lookup to identify publicly indexed services and open ports associated with the domain.
* **FR-5.5:** The system shall identify technologies publicly visible on the domain using Wappalyzer, including web server software, CMS platforms, and web frameworks.
* **FR-5.6:** The system shall execute all OSINT lookups in parallel to minimise total scan time.
* **FR-5.7:** The system shall gracefully handle unavailable data sources, completing the scan with partial results rather than failing entirely.
* **FR-5.8:** The system shall use Hunter.io to identify publicly discoverable email addresses associated with the submitted domain, and shall classify each discovered address by type (personal or generic) and confidence score.

#### FR-6: Risk Assessment
* **FR-6.1:** The system shall assign a risk level to each finding discovered during the OSINT scan (Critical, High, Medium, Low, Informational).
* **FR-6.2:** The system shall calculate a risk summary for the scanned domain based on aggregated findings, including the total finding count broken down by severity level (Critical, High, Medium, Low, Informational).
* **FR-6.3:** The system shall provide a brief human-readable explanation for each finding, describing why it is considered a risk.
* **FR-6.4:** The system shall include actionable remediation recommendations for each identified finding.

#### FR-7: Audit Logging
* **FR-7.1:** The system shall log every scan initiation event, recording the domain, timestamp, and originating IP address.
* **FR-7.2:** The system shall log every report access event, recording the scan ID, timestamp, and whether the accessing user was authenticated or anonymous.
* **FR-7.3:** The system shall log every report download event, recording the user ID (if authenticated), scan ID, report type (brief or detailed), and timestamp.
* **FR-7.4:** The system shall store all audit logs in an append-only format. This shall be enforced by denying UPDATE and DELETE privileges on the `audit_logs` table at the database level.


### Phase 2

 #### FR-8: Domain Ownership Verification
  * **FR-8.1:** The system shall require that an asset's domain ownership is verified before
    a Phase 2 automated vulnerability scan can be initiated on that asset.
  * **FR-8.2:** The system shall allow authenticated users to initiate a domain ownership
    verification request for an asset registered to their account.
  * **FR-8.3:** The system shall generate a unique cryptographic token for each verification
    request and instruct the user to create a DNS TXT record at the root domain level
    (host `@`) with the record value set to the provided token.
  * **FR-8.4:** The system shall verify ownership by performing a DNS TXT record query
    (e.g. via `dig`/`nslookup`-equivalent resolution) against the root of the target domain
    and confirming that the issued token is present among the returned TXT values.
  * **FR-8.5:** The system shall allow the user to trigger a verification check on demand;
    the system performs a single DNS TXT lookup at that point and returns the result
    immediately, marking the request as failed if the token is not present.
  * **FR-8.6:** The system shall mark the asset as verified (`isVerified: true`, recording
    `verifiedAt`) upon successful token confirmation via DNS TXT lookup.
  * **FR-8.7:** The system shall record the most recent verification state against the asset,
    including the current status (pending, verified, failed), the method used (`dns_txt`),
    the issued token, and the timestamp of the last check. Only the latest state is retained;
    prior attempts are overwritten.


#### FR-9: Automated External Vulnerability Scan
 * **FR-9.1:** The system shall allow authenticated users to initiate a Phase 2 vulnerability
    scan only against assets whose domain ownership has been verified (FR-8.6).
* **FR-9.2:** The system shall restrict all Phase 2 scanning to the external perimeter only;
  no internal network scanning, authenticated web application testing, or social engineering
  simulation shall be performed.
* **FR-9.3:** The system shall enumerate open ports and identify service banners on the
  verified domain's external IP address.
* **FR-9.4:** The system shall assess the TLS/SSL configuration of the target domain,
  identifying weak cipher suites, expired certificates, and protocol downgrades.
* **FR-9.5:** The system shall evaluate HTTP security headers on the target domain and flag
  missing or misconfigured headers (e.g. HSTS, CSP, X-Frame-Options).
* **FR-9.6:** The system shall match discovered service versions against CVE feeds to
  identify known vulnerabilities, associating each match with its CVE ID and CVSS score.
* **FR-9.7:** The system shall assign a CVSS-aligned severity level (Critical, High, Medium,
  Low, Informational) to each finding produced by the Phase 2 scan.
* **FR-9.8:** The system shall provide actionable remediation guidance for each finding,
  including references to authoritative sources where applicable.
* **FR-9.9:** The system shall execute each Phase 2 scan inside an isolated Docker container,
    scoped to a single scan, to prevent cross-client data leakage and resource contention.
* **FR-9.10:** The system shall display real-time scan progress to the authenticated user
  who initiated the scan, updating without requiring a page reload.
* **FR-9.11:** The system shall complete gracefully if individual scan sub-tasks fail,
  returning partial results rather than failing the entire scan.

#### FR-10: Phase 2 Scan Results
* **FR-10.1:** The system shall display all Phase 2 findings grouped and filterable by
  severity level (Critical, High, Medium, Low, Informational).
* **FR-10.2:** The system shall generate a delta report for any Phase 2 scan where a
  previous scan exists for the same asset, highlighting new findings and resolved findings.
* **FR-10.3:** The system shall generate a downloadable PDF report for completed Phase 2
  scans, accessible only to authenticated users belonging to the asset's organisation.
* **FR-10.4:** The system shall display the CVE ID, CVSS score, description, and
  remediation guidance for each vulnerability-linked finding.

#### FR-11: Scan Scheduling
* **FR-11.1:** The system shall allow authenticated users to configure a recurring scan
  schedule for a verified asset, specifying a frequency (weekly or monthly).
* **FR-11.2:** The system shall automatically trigger a new Phase 2 scan at the configured
  interval without requiring manual user action.
* **FR-11.3:** The system shall allow authenticated users to view, update, and cancel an
  existing scan schedule for an asset they own.
* **FR-11.4:** The system shall record the `nextRun` and `lastRun` timestamps for each
  active schedule and update them after each triggered scan.
* **FR-11.5:** The system shall notify the asset owner when a scheduled scan completes,
  via an in-platform notification.


# PenFlow: OSINT Scanning Engine Use Cases

## User Stories
* **US-01:** As a PenFlow User, I want to initiate an OSINT scan on this domain so that I can discover potential vulnerabilities and exposed assets.
* **US-02:** As a PenFlow User, I want to view a summarized scan report so that I can quickly understand the risk level and asset impact of my target infrastructure.
* **US-03:** As a PenFlow User, I want to access my scan history so that I can track previous assessments and easily locate past reports.
* **US-04:** As a PenFlow User, I want to email the generated PDF report so that I can easily share the intelligence findings with my team or clients.
* **US-05:** As a PenFlow User, I want to securely authenticate and log in so that my sensitive scan data is protected and private.
* **US-06:** As a PenFlow User, I want to download my scan report as a PDF so I can store it offline or attach it to internal tickets. 
* **US-07:** As a PenFlow User, I want to cancel a running scan so that I don't waste system resources if I entered the wrong domain.

---

## 1. Actors
An actor denotes a business role played by (and on the behalf of) a set of business entities.

* **PenFlow User:** This is the primary client interacting with our Next.js frontend to initiate scans and view results.
* **OSINT Workers:** The automated backend subsystems responsible for executing the intelligence gathering (which includes subdomains, open ports, breached credentials).

---

## 2. Use Case Specifications

### UC-01: Initiate OSINT Scan
**Actor(s):** PenFlow User

**High-Level Description:**
* **TUCBW** the User entering a target domain and clicking the "Start Scan" button on the dashboard.
* **TUCEW** the system presents the user with the scan dashboard, indicating the scan has successfully started.

**Expanded Specification:**
1. The PenFlow User navigates to the New Scan page.
2. The user inputs the target domain and optionally provides an email address.
3. The user clicks "Start Scan".
4. The system validates the domain format.
5. The system confirms the scan has been successfully initiated.
6. The system redirects the user to the Executive Summary dashboard.

### UC-02: View Scan Report
**Actor(s):** PenFlow User

**High-Level Description:**
* **TUCBW** the User clicks on a completed scan from their dashboard or receives a redirect after initiating a new scan.
* **TUCEW** the User successfully views the aggregated intelligence data.

**Expanded Specification:**
1. The PenFlow User requests to view the summary for a specific scan.
2. The system retrieves the base scan details and findings.
3. The system aggregates the risk snapshot and asset impact breakdown.
4. The system retrieves and truncates the top findings for preview.
5. The system presents the Executive Summary dashboard to the user.

### UC-03: View Scan History
**Actor:** PenFlow User

**High-Level Description:**
* **TUCBW** the User clicks the History or All Scans tab from the main navigation menu.
* **TUCEW** the User views a structured list of all their historical scans, including current statuses and timestamps.

**Expanded Specification:**
1. The PenFlow User navigates to the Scan History page.
2. The system retrieves all historical scan records associated with the user's account.
3. The system orders the records by creation date (newest first).
4. The system displays the formatted list of scans, allowing the user to view which are Pending, Running, or Completed.

### UC-04: Send Scan Report via Email
**Actor:** PenFlow User

**High-Level Description:**
* **TUCBW** the PenFlow User clicks the "Email Report" button on the Executive Summary dashboard and submits a target email address.
* **TUCEW** the system verifies the PDF report exists and successfully queues the email for delivery.

**Expanded Specification:**
1. The PenFlow User requests to email the report for a specific scan by providing a target email address.
2. The system validates the email address format.
3. The system verifies that a final PDF report document has been generated for that scan.
4. If the report is missing or still generating, the system displays an error message to the user.
5. If the report exists, the system queues the report for email dispatch.
6. The system displays a confirmation message to the user indicating that the email has been queued.

### UC-05: Log In
**Actor:** PenFlow User

**High-Level Description:**
* **TUCBW** an unauthenticated user attempts to access a protected route or clicks the "Login" button.
* **TUCEW** the system verifies their identity and grants access to the dashboard.

**Expanded Specification:**
1. The user navigates to the login page.
2. The user submits their credentials.
3. The system validates the credentials.
4. The system grants access and redirects the authenticated user to the main dashboard.

### UC-06: Download PDF Report
**Actor:** PenFlow User

**High-Level Description:**
* **TUCBW** the PenFlow User clicks the "Download PDF" button on the Executive Summary dashboard.
* **TUCEW** the system retrieves the generated PDF and streams it to the user. 

**Expanded Specification:**
1. The PenFlow User requests the PDF download for a specific scan.
2. The system verifies that the report generation is complete.
3. The system retrieves the final report file.
4. The system prompts the user's browser to save the PDF file locally.

### UC-07: Cancel Running Scan
**Actors:** PenFlow User

**High-Level Description:**
* **TUCBW** the user clicks "Cancel" on a scan that is currently in a "Running" or "Pending" state.
* **TUCEW** the system terminates the background worker process and marks the scan as canceled.

**Expanded Specifications:**
1. The User requests to cancel a specific scan.
2. The system verifies the user has permission to modify this scan and that the scan is not already completed.
3. The system halts the background scanning tasks.
4. The system marks the scan as canceled.
5. The system updates the UI to reflect the canceled status to the user.


### Domain Model

![PenFlow Demo 2 Domain Model](Domain%20Model/domainModeldemo2.drawio.png)

## Non-functional Requirements

### NFR-1: Performance
Our system's API endpoints respond to user requests within 2 seconds for 95% of requests under standard operating conditions. Futhermore due to the parallel execution of pur OSINT lookups, Phase 1 CTEM scans must complete and generate initial results within xx seconds.

### NFR-2: Secuirity
All user passwords and sensitive scan data must be encrypted at rest. Assitionally we enforce strict tenant isolation, all of our Phase 2, active scans, must be executed within isolated short-lived worker containers that are destroyed upon completion to prevent crossclient data leakage.

### NFR-3: Reliability
The core of our PenFlow web interface and user dashboard shall achieve 99% uptime. In the event of a third party OSINT API failure, our background worker processes must successfully recover within x seconds and gracefully compile a partial report, maintaining a 1% system crash rate.

### NFR-4: Scalability
The system's worker queue architecture must automatically support horizontal scaling, being able to handle an increase in workload of up to xxx% without requiring manual architectural changes and without experiencing more than xx% decrease in the speed of report generation.

### NFR-5: Maintainability
Our backend services and worker modules must maintain a minimum of 80% automated test coverage (all types of tests) to ensure reliable deployments. 