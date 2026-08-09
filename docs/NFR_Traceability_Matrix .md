# PenFlow — NFR Traceability Matrix

This table joins each quantified quality requirement (SRS) to the architectural tactic claimed to satisfy it (SAS), and the test/tool used to verify it.

| ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
|----|------------------------|---------------|-------------|------------------|
| QR-01 | P95 API response time under 2 seconds for all REST endpoints under normal load | Asynchronous task execution + fast acknowledgement (4.3 Performance) | Jmeter | <2s / TBD |
| QR-02 | Phase 1 CTEM scan completes within 60 seconds for 90% of requests, bounded by slowest single OSINT lookup | Asynchronous aggregation of parallel OSINT providers (1, 4.3) | Jmeter / custom load script | <60s / TBD |
| QR-03 | System remains stable at 100 concurrent users; response time degradation <50% under peak load vs. baseline | Horizontal scaling of workers + queue-based load leveling via RabbitMQ (4.2 Scalability) | Jmeter (sustained + burst load) | <50% degradation / TBD |
| QR-04 | No cross-client data leakage under concurrent Phase 2 scan execution | Isolated, short-lived worker containers destroyed on completion (4.6 Security, NFR-2) | pytest security suite | 0 leaks / TBD |
| QR-05 | Unauthenticated requests to protected endpoints return 401; cross-user data access attempts (IDOR) return 403 | JWT-based auth (Auth0) with RBAC + information hiding (4.6 Security) | pytest security suite | 401 / 403 / TBD |
| QR-06 | Phase 2 scan against unverified asset returns 403 | Domain ownership verification gate (1 Phase 2) | pytest security suite | 403 / TBD |
| QR-07 | Rate limiter returns 429 on 4th scan submission from same IP within 1 hours | IP-based rate limiting (7.3 Regulatory/Ethical Constraints) | pytest security suite | 429 / TBD |
| QR-08 | No sensitive data (API keys, credentials) exposed in API responses or logs | AWS Secrets Manager + information hiding (4.6 Security) | pytest security suite | 0 exposures / TBD |
| QR-09 | System recovers from third-party OSINT API failure and compiles partial report; <1% crash rate | Partial failure tolerance + retry with bounded calls (4.4 Reliability) | pytest + fault injection | <1% crash rate / TBD |
| QR-10 | Core web interface and dashboard achieve 99% uptime | Independent ECS deployment + ALB health checks + auto-replacement (4.1 Availability) | UptimeRobot| ≥99% / TBD |
