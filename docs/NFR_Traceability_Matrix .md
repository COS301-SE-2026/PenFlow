    # PenFlow — NFR Traceability Matrix


    ## Performance (tool: TBD)
    | ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
    |----|------------------------|---------------|-------------|------------------|
    | QR-01 | P95 API response time under 2 seconds for all REST endpoints under normal load | Asynchronous task execution + fast acknowledgement (4.3 Performance) | k6 | <2s / TBD |
    | QR-02 | Phase 1 CTEM scan completes within 60 seconds for 90% of requests, bounded by slowest single OSINT lookup | Asynchronous aggregation of parallel OSINT providers (1, 4.3) | k6 | <60s / TBD |

    ## Scalability (tool: k6)
    | ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
    |----|------------------------|---------------|-------------|------------------|
    | QR-03 | System remains stable at 100 concurrent users; response time degradation <50% under peak load vs. baseline | Horizontal scaling of workers + queue-based load leveling via RabbitMQ (4.2 Scalability) | k6 | <50% degradation / TBD |

    ## Reliability (tool: pytest + fault injection)
    | ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
    |----|------------------------|---------------|-------------|------------------|
    | QR-04 | System recovers from third-party OSINT API failure and compiles partial report; <1% crash rate | Partial failure tolerance + retry with bounded calls (4.4 Reliability & Fault Tolerance) | pytest | <1% crash rate / TBD |

    ## Availability (tool: UptimeRobot)
    | ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
    |----|------------------------|---------------|-------------|------------------|
    | QR-05 | Core web interface and dashboard achieve 99% uptime | Independent ECS deployment + ALB health checks + auto-replacement (4.1 Availability) | UptimeRobot | ≥99% / TBD |

    ## Security (tool: OWASP ZAP + pytest security suite)
    | ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
    |----|------------------------|---------------|-------------|------------------|
    | QR-06 | No medium-or-above risk alerts on staging from automated vulnerability scanning; passwords and sensitive scan data encrypted at rest | Transport security (HTTPS/TLS) + information hiding (4.6 Security) | OWASP ZAP | 0 medium+ / TBD |
    | QR-07 | Unauthenticated requests return 401; cross-user (IDOR) and unverified-asset requests return 403; no cross-client data leakage under concurrent Phase 2 scan execution | JWT-based auth (Auth0) with RBAC + isolated, short-lived worker containers destroyed on completion (4.6 Security, 1 Phase 2) | pytest | 401 / 403 / 0 leaks / TBD |
    | QR-08 | No sensitive data (API keys, credentials) exposed in API responses or logs; rate limiter returns 429 on 4th scan submission from same IP within 1 hour | AWS Secrets Manager + information hiding (4.6 Security) + IP-based rate limiting (7.3 Regulatory/Ethical Constraints) | pytest | 0 exposures / 429 / TBD |

    ## Maintainability (tool: ESLint / ruff)
    | ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
    |----|------------------------|---------------|-------------|------------------|
    | QR-09 | 100% of merged PRs pass static code analysis with zero linting errors | Established coding standards + CI quality gates (4.5 Maintainability & Evolvability) | ESLint / ruff | 0 errors / TBD |
    | QR-10 | Backend services and worker modules maintain ≥80% automated test coverage | CI coverage gate (4.5 Maintainability & Evolvability) | pytest-cov | ≥80% / TBD |

    ## Usability (tool: Google Lighthouse)
    | ID | Quantified Requirement | Tactic in SAS | Test / Tool | Target / Actual |
    |----|------------------------|---------------|-------------|------------------|
    | QR-11 | Primary user-facing pages (dashboard, scan results) achieve a Lighthouse accessibility score of at least 80 | Not covered by SAS §4 (no formal usability tactic documented) | Google Lighthouse | ≥80 / TBD |
    | QR-12 | Scan results and vulnerability findings presented in a format understandable to technical and non-technical users | Not covered by SAS §4 (no formal usability tactic documented) | Manual review | Pass / TBD |
