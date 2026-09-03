# PenFlow - NFR Traceability Matrix
 
## Performance (tool: k6)
| ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
|----|------------------------|---------------|-------------|------------------|
| QR-01 | P95 API response time under 2 seconds for  REST endpoints under normal load | Asynchronous task execution + fast acknowledgement (4.2 Performance) | k6 | <2s / 208.23ms (p95)  |
| QR-02 | Phase 1 CTEM scan completes within 60 seconds for 90% of requests, bounded by slowest single OSINT lookup | Asynchronous aggregation of parallel OSINT providers (1, 4.2) | k6 | <60s / 34.09s (p90); all 10 runs returned "partial" status |
| QR-03 | Phase 2 active vulnerability scan completes within 30 seconds for 90% of requests, bounded by the sequential worker pipeline rather than a single lookup | Asynchronous task execution + fast acknowledgement (4.2 Performance); pipelined active-scan workers, dependent stages (5.4 Worker Pipeline Architecture, 7.5 Worker Pipeline Constraints) | k6 | <30s / 25.1s (p90)  |
 
## Scalability (tool: k6)
| ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
|----|------------------------|---------------|-------------|------------------|
| QR-04 | System remains stable at 100 concurrent users; response time degradation <50% under peak load vs. baseline | Horizontal scaling of workers + queue-based load leveling via RabbitMQ (4.1 Scalability) | k6 | <50% degradation / 0.00% error rate at up to 110 VUs  (degradation vs. isolated baseline not yet measured) |
 
## Reliability (tool: k6, UptimeRobot)
| ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
|----|------------------------|---------------|-------------|------------------|
| QR-05 | System recovers from third-party OSINT API failure and compiles partial report; <1% crash rate | Partial failure tolerance + retry with bounded calls (4.3 Reliability) | k6 | <1% crash rate / 0% crash rate (0/10); 10/10 runs returned "partial" - graceful degradation observed under real OSINT conditions |
| QR-06 | Availability  achieve 99% uptime | Independent ECS deployment + ALB health checks + auto-replacement (4.3 Reliability) | UptimeRobot | ≥99% / TBD |
 
## Security (tool: OWASP ZAP + k6)
| ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
|----|------------------------|---------------|-------------|------------------|
| QR-07 | No medium risk alerts on staging from automated vulnerability scanning; passwords and sensitive scan data encrypted at rest | Transport security (HTTPS/TLS) + information hiding (4.5 Security) | OWASP ZAP | 0 medium+ / 2 |
| QR-08 | Unauthenticated requests return 401; cross-user requests return 404 (ownership is enforced via a user_id-scoped lookup, not an explicit 403 check) | JWT-based auth (Keycloak) with RBAC + isolated, short-lived worker containers destroyed on completion (4.5 Security, 1 Phase 2) | k6 | 401 / 404 / 401 confirmed, 0 secrets leaked; 404 cross-user check pending (needs AUTH_TOKEN) |
| QR-09 | No sensitive data (API keys, credentials) exposed in API responses or logs; rate limiter returns 429 on 4th scan submission from same IP within 10 minutes | AWS Secrets Manager + information hiding (4.5 Security) + IP-based rate limiting (7.3 Regulatory/Ethical Constraints) | k6 | 0 exposures / 429 confirmed, 0 secrets leaked |
 
## Maintainability (tool: ESLint / ruff)
| ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
|----|------------------------|---------------|-------------|------------------|
| QR-10 | 100% of merged PRs pass static code analysis with zero linting errors | Established coding standards + CI quality gates (4.4 Maintainability & Evolvability) | ESLint / ruff | 0 errors / 0errors |
| QR-11 | Backend services and worker modules maintain ≥80% automated test coverage | CI coverage gate (4.4 Maintainability & Evolvability) | pytest-cov | ≥80% / 64.5% |
 
## Usability (tool: Google Lighthouse)
| ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
|----|------------------------|---------------|-------------|------------------|
| QR-12 | Primary user-facing pages (dashboard, scan results) achieve a Lighthouse accessibility score of at least 80 | Not covered by SAS  | Google Lighthouse | >80 / >=80% |
