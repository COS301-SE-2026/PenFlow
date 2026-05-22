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
