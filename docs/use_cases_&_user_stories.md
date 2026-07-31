# PenFlow: OSINT Scanning Engine Use Cases

## User Stories
* **US-01:** As a PenFlow User, I want to initiate an OSINT scan on this domain so that I can discover potential vulnerabilities and exposed assets.
* **US-02:** As a PenFlow User, I want to view a summarized scan report so that I can quickly understand the risk level and asset impact of my target infrastructure.
* **US-03:** As a registered PenFlow User, I want to access my scan history so that I can track previous assessments and easily locate past reports.
* **US-04:** As a PenFlow User, I want to email the generated PDF report so that I can easily share the intelligence findings with my team or clients.
* **US-05:** As a PenFlow User, I want to securely authenticate and log in so that my sensitive scan data is protected and private.
* **US-06:** As a PenFlow User, I want to download my scan report as a PDF so I can store it offline or attach it to internal tickets. 
* **US-07:** As a PenFlow User, I want to cancel a running scan so that I don't waste system resources if I entered the wrong domain.
* **US-08:** As a registered PenFlow user, I want to verify ownership of my domain via a DNS TXT record so that I can securely authorize active vulnerability scans on my infrastructure.
* **US-09:** As a PenFlow system, I need to isolate each active scan in a dedicated worker container so that cross client data leakage is prevented during execution.
* **US-10:** As a registered PenFlow user I want to receive a delta report after an active scan completes so that I can easily identify newly introduced or resolved findings. 
* **US-11:** As a registered PenFlow user, I want to view a detailed history of a specific verified asset so that I can track how its security has changed over time.
* **US-12:** As a registered PenFlow user I want to view a high level summary so that I can quickly understand my organization's external risk score and prioritize critical remediations.
* **US-13:** As a registered PenFlow user, I want to add a new domain to my workspace so that I can begin the verification and scanning process.
* **US-14:** As a registered PenFlow user I want to view all my domains in a list so that I can easily manage and monitor the attack surface.
* **US-15:** As a registered PenFlow user I want to search and filter my domains so that I can quickly locate a specific target within a large list.
* **US-16:** As a registered PenFlow user I want to remove a domain from my account so that it is no longer tracked or scanned by the system.

## 2. Use Case Specifications

### UC-01: Log In
**Actor:** PenFlow User

**Pre-conditions:** None

**Trigger:** The user attempts to access a protected route or clicks Login.

**Main Success Scenario:**
1. User submits their credentials.
2. The system validates the credentials against the secure authentication provider.
3. The system enforces MFA checks.
4. The system issues a JWT and redirects to the dashboard.

**Alternate/Exception Flow:**
Invalid Credentials: The system denies access and displays a generic error message.

**Post-condition:** The user is securely authenticated and a tenant context is established.


### UC-02: Verify Domain Ownership
**Actors:** Registered PenFlow User, DNS Provider
**Pre-conditions:** User is successfully authenticated and logged into the system.
**Trigger:** The user adds a new domain and requests (active) scanning capabilities.

**Main Success Scenario:**
1. The user inputs the target domain into our dashboard.
2. The system generates a unique verification token to be used as a DNS TXT record.
3. The user updates their domain's DNS records with the provided token.
4. The user clicks "Verify".
5. The system queries the DNS, upon finding the matching record, the domain ownership is verified. 

**Alternate/Exception Flow:**
Record Not Found: The system cannot find the TXT record and prompts the user to try again. (Potentially due to propagation delay or user error)

**Post-condition:** The domain is securely linked to the user's account and authorized for active Phase 2 scanning.

### UC-03: View Scan History
**Actor:** Registered PenFlow User

**Pre-conditions:** The user is authenticated 

**Trigger:** The user clicks the history tab.

**Main Success Scenario:**
1. Our system retrieves all historical scan records from the user's specific database schema.
2. The system displays an ordered list of past scans.

**Alternate/Exception Flow:**
Empty History: The user has no previous scans. The system displays a call to action to initiate their first scan.

**Post-condition:** The historical list is successfully rendered.

### UC-04: Initiate OSINT Scan (Passive)
**Actor(s):** Unregistered PenFlow User

**Pre-conditions:** None

**Trigger:** The user inputs a domain and clicks scan.

**Main Success Scenario:**
1. The user navigates to the New Scan Page.
2. The user inputs the target domain and (optionally) an email address.
3. The system validates the domain format.
4. The system fires all OSINT lookups concurrently via our background workers.
5. The system redirects the user to the live progress dashboard.

**Alternate/Exception Flow:**
Rate Limit Exceeded: Our system denies the scan request and prompts the user to try again later.

**Post-condition:** A scan job is successfully queued.

### UC-05: Execute Phase 2 Vulnerability Scan
**Actors:** OSINT/Scan Worker
**Pre-conditions:** The domain is verified and the scan is triggered.
**Trigger:** After selecting one of the verified domains the user clicks scan.

**Main Success Scenario:**
1. The scan worker initiates port and service enumeration on the external IP range. 
2. The system maps discovered services against our datasets and feeds (NVD and CVE respectively)

**Alternate/Exception Flow:**
Target Unreachable: The system detects the host is down, logs the failure and alerts our user.

**Post-condition:** Raw vulnerability data is securely written to the user's database schema.

### UC-06: Cancel Running Scan
**Actors:** PenFlow User

**Pre-conditions:** A scan is actively running in the background.

**Trigger:** The user clicks cancel scan.

**Main Success Scenario:**
1. The system intercepts the termination request.
2. The system then destroys the short lived container running the scan job.
3. The database updates the scan status to "Canceled".

**Alternate/Exception Flow:**
Race Condition: The background worker finishes the scan milliseconds before the cancel request. The system informs the user the scan is already complete.

**Post-condition:** System resources are freed and the scan is officially halted.

### UC-07: View Detailed Target History 
**Actors:** PenFlow User
**Pre-conditions:** The user is authenticated.
**Trigger:** Our user navigates to a specific verified asset's history page.

**Main Success Scenario:**
1. The system retrieves all historical active scans for the selected domain.
2. The system displays a timeline showing the resolution or introduction of vulnerabilities over time.

**Alternate/Exception Flow:**
Unauthorized Access: The system blocks the request if the JWT context does not match the requested asset.

**Post-condition:** The UI displays the historical timeline and the system logs the data according to findings, assets and services. 

### UC-08: View Scan Report
**Actor(s):** Registered PenFlow User

**Pre-condition:** A scan ID exists and has at least partially completed.

**Trigger:** The user is redirected to the dashboard or clicks a report link.

**Main Success Scenario:**
1. The system retrieves a scan's details and findings from the database.
2. Our system maps disparate tool results to a unified schema.
3. The dashboard renders the risk snapshot and asset impact.

**Alternate/Exception Flow:**
Partial API Failure: A third party source is rate limited or unavailable. Our system then gracefully completes the report with the available data.

**Post-condition:** The user views the aggregated OSINT intelligence.

### UC-09: Generate Phase 2 Active Reports 
**Actors:** System Worker

**Pre-conditions:** A Phase 2 scan has successfully been 
completed. 

**Trigger:** The scan worker finalises the vulnerability assessment.

**Main Success Scenario:**
1. Our system gathers the findings according to assets, findings and services.
2. The system generates a report highlighting new vulnerabilities and resolved findings.

**Alternate/Exception Flow:**
First Scan: If no previous scan exists, our system generates a standard baseline report.

**Post-condition:** A formatted report is available for download and securely stored.

### UC-10: View Phase 2 Executive Summary
**Actors:** Registered PenFlow User

**Pre-conditions:** The user is authenticated 

**Trigger:** The user logs in and navigates to the main Phase 2 dashboard. 

**Main Success Scenario:**
1. The system aggregates data across all verified domains.
2. The system displays high level risk indicators, highest CVSS scores, and pending remediation tasks.

**Alternate/Exception Flow:**
No verified domains: Our system detects the user has no verified targets. The system will then display an empty state with a call to actions promting the user to navigate to the domains tab and verify a target.

**Post-conditions:** The UI successfully renders the aggregated risk summary.

### UC-11: Download PDF Report
**Actor:** PenFlow User

**Pre-conditions:** A scan has completed successfully.

**Trigger:** The user clicks download pdf.

**Main Success Scenario:**
1. The system generates a pre-signed URL to securely access the namespaced object storage path.
2. The system retrieves the final branded pdf report.
3. The browser prompts the user to save the file.

**Alternate/Exception Flow:**
Missing File: The pdf was deleted or failed to compile. Our system queues a new generation task and asks the user to wait.

**Post-condition:** The pdf is successfully downloaded to the client's local machine.

### UC-12: Send Scan Report via Email
**Actor:** PenFlow User, SMTP Service

**Pre-conditions:** A scan has been completed and a PDF report has been generated.

**Trigger:** User submits an email address on the summary dashboard.

**Main Success Scenario:**
1. Our system verifies the final PDF exists.
2. The system queues the report for email dispatch via an external mail provider.
3. The system displays a success confirmation.

**Alternate/Exception Flow:**
Delivery Failure: The SMTP service is unreachable. The system logs the error and notifies the user to try again.

**Post-condition:** The PDF is successfully dispatched to the provided email address.

### UC-13: Add Domain
**Actor:** Registered Penflow User

**Pre-condition:** The user is authenticated.

**Trigger:** The user clicks "+ Add Domain" on the domain dashboard.

**Main Success Scenario:** 
1. The user inputs a valid domain name.
2. System validates the domain format.
3. The system saves the domain to the database with a "Pending" status.
4. The system seamlessly transitions the user to the Verify Domain Ownership process.

**Alternate/Exception Flow:**
Duplicate Domain: The domain does not get a new entry, the user that the domain already exists.

**Post-condition:**  The new domain is recorded in the system and is ready for ownership verification.

### UC-14: View Domains List
**Actor:** Registered PenFlow User

**Pre-conditions:** The user is authenticated.

**Trigger:** The user navigates to the Domains tab.

**Main Success Scenario:**
1. The system queries the database for all domains associated with the user's account.
2. The system categorises the domains via status.
3. The system renders the domains in a data grid showing the domain name, status, date added  and last checked date.

**Alternate/Exception Flow:** 
No Domains Found: The user has not added any domains yet. The system displays an empty state graphic with a call to action to add their first domain.

**Post-condition:** The user's domain inventory is successfully displayed.

### UC-15: Search and Filter Domains
**Actor:** Registered PenFlow User

**Pre-conditions:** The user is authenticated and has at least one domain in their list.

**Trigger:**  The user types into the search bar or uses the status filter tab.

**Main Success Scenario:**
1. The user inputs a search string or selects a specific filter.
2. The system dynamically filters the displayed list in the UI to match the specific query or status.
3. The data grid updates immediately to show only the relevant domains.

**Alternate/Exception Flow:**
No Result Match: The user searches for a domain that does not exist in their list, our system then displays a message saying no domains found.

**Post-condition:** The UI is updated to reflect the user's search or filter criteria.

### UC-16: Remove Domain
**Actor:** Registered PenFlow User

**Pre-conditions:** The user is authenticated and the domain exists in their account.

**Trigger:** The user clicks the Remove action on a specific domain.

**Main Success Scenario:**
1. The user clicks remove.
2. The system removes the domain record and cascades the deletion to associated historical scan data.
3. The UI gets updated to remove the domain from the list.

**Alternate/Exception Flow:**
The system loses connection while trying to delete the record. The system aborts the process and will require the user to try again.

**Post-condition:** The domain and its associated data are permanently removed from the user's workspace.
