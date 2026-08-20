# Software Requirements Specification (SRS) Document

## Non-functional Requirements

Each category below is verified by a single external tool/service rather than bespoke test code, so one tool run can satisfy several quantified requirements at once. Every bullet maps 1:1 to a QR-id in the [NFR Traceability Matrix](NFR_Traceability_Matrix%20.md).

### NFR-1: Performance
*Tool: TBD*
- P95 API response time ≤ 2 seconds for all REST endpoints under standard operating conditions (QR-01)
- Phase 1 CTEM scans complete and generate initial results within 60 seconds for 90% of requests, bounded by the slowest single OSINT lookup (QR-02)

### NFR-2: Scalability
*Tool: k6*
- The worker queue architecture scales horizontally without manual architectural changes as workload increases
- System remains stable at 100 concurrent users, with response time degradation < 50% vs. baseline under peak load (QR-03)

### NFR-3: Reliability
*Tool: pytest + fault injection*
- On third-party OSINT API failure, background workers recover and gracefully compile a partial report (QR-04)
- System-wide crash rate stays below 1% across background worker executions (QR-04)

### NFR-4: Availability
*Tool: UptimeRobot*
- The core PenFlow web interface and user dashboard maintain ≥ 99% uptime (QR-05)

### NFR-5: Security
*Tool: OWASP ZAP + pytest security suite*
- No medium-or-above risk vulnerabilities (e.g. missing security headers, insecure cookie configuration, common injection vectors) as verified by automated scanning against staging; sensitive data (passwords, scan data) encrypted at rest (QR-06)
- Access is restricted by JWT-based auth + RBAC: unauthenticated requests return 401, cross-user/unverified-asset requests return 403; Phase 2 active scans run in isolated, short-lived worker containers destroyed on completion, preventing cross-client data leakage (QR-07)
- No sensitive data (API keys, credentials) is exposed in API responses or logs; repeated scan submissions from the same IP are rate-limited (QR-08)

### NFR-6: Maintainability
*Tool: ESLint (frontend/Node) + ruff (backend/Python)*
- All merged pull requests pass static analysis with zero linting errors, enforced via CI (QR-09)
- Backend services and worker modules maintain ≥ 80% automated test coverage (QR-10)

### NFR-7: Usability
*Tool: Google Lighthouse*
- Primary user-facing pages (dashboard, scan results) achieve a Lighthouse accessibility score of at least 80 (QR-11)
- Scan results and vulnerability findings are presented in a format understandable to both technical and non-technical users (manual usability review, QR-12)
