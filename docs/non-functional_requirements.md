# Software Requirements Specification (SRS) Document

## Non-functional Requirements


### NFR-1: Performance
*Tool: k6*
- P95 API response time ≤ 2 seconds for REST endpoints under standard operating conditions (QR-01)
- Phase 1 CTEM scans complete and generate a terminal result within 60 seconds for 90% of requests, bounded by the slowest single OSINT lookup rather than the sum of all lookups (QR-02)
- Phase 2 active vulnerability scans complete within 30 seconds for 90% of requests, bounded by the sequential worker pipeline rather than a single lookup (QR-03)

### NFR-2: Scalability
*Tool: k6*
- The worker queue architecture scales horizontally without manual architectural changes as workload increases
- System remains stable at 100 concurrent users, with response time degradation < 50% vs. baseline under peak load (QR-04)

### NFR-3: Reliability
*Tool: k6, UptimeRobot*
- On third-party OSINT API failure, background workers recover and gracefully compile a partial report; system-wide crash rate stays below 1% across scan requests (QR-05)
- The core PenFlow web interface and user dashboard maintain ≥ 99% uptime (QR-06)

### NFR-4: Security
*Tool: OWASP ZAP + k6*
- No medium-or-above risk vulnerabilities (e.g. missing security headers, insecure cookie configuration, common injection vectors) as verified by automated scanning against staging; sensitive data (passwords, scan data) encrypted at rest (QR-07)
- Access is restricted by JWT-based auth (Keycloak) + RBAC: unauthenticated requests return 401; cross-user requests return 404 (ownership is enforced via a user_id-scoped lookup, not an explicit 403 check) (QR-08)
- No sensitive data (API keys, credentials) is exposed in API responses or logs; repeated scan submissions from the same IP are rate-limited - 429 on the 4th submission within 10 minutes (QR-09)

### NFR-5: Maintainability
*Tool: ESLint (frontend/Node) + ruff (backend/Python) + pytest-cov*
- All merged pull requests pass static analysis with zero linting errors, enforced via CI (QR-10)
- Backend services and worker modules maintain ≥ 80% automated test coverage (QR-11)

### NFR-6: Usability
*Tool: Google Lighthouse*
- Primary user-facing pages (dashboard, scan results) achieve a Lighthouse accessibility score of at least 80 (QR-12)
