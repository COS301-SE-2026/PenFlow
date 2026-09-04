# PenFlow - NFR Testing
 
---
 
## Performance
 
### QR-01 - API response time under normal load
 
**Objective:** Validate that API response times stay within target under normal load.
 
**Tool used:** k6
 
**Test performed:** `tests/k6/load_test.js`, `performance` scenario - 10 constant virtual users hitting `GET /api/v1/health` for 30s against `https://pen-flow.com`.
 
**Evidence:**
 
![QR-01 load test result](proof/load.png)
 
**Result:** p(95) response time **208.23ms** against a target of <2s - **passes**.
 
---
 
### QR-02 - Phase 1 CTEM scan completion time
 
**Objective:** Validate that the Phase 1 CTEM scan completes within target, bounded by the slowest single OSINT lookup.
 
**Tool used:** k6
 
**Test performed:** `tests/k6/phase1_scan_completion_test.js` - 10 sequential Phase 1 CTEM scans triggered and polled to completion.
 
**Evidence:**
 
![QR-02 Phase 1 scan completion result](proof/phases1scan.png)
 
**Result:** p(90) completion time **34.09s** against a target of <60s - **passes**. All 10 runs returned `"partial"` status rather than `"completed"` (at least one OSINT source failed/rate-limited during each run - expected graceful-degradation behavior, not a defect).
 
---
 
### QR-03 - Phase 2 active vulnerability scan completion time
 
**Objective:** Validate that the Phase 2 active scan completes within target, bounded by the sequential worker pipeline.
 
**Tool used:** k6
 
**Test performed:** `tests/k6/phase2_scan_completion_test.js` - Phase 2 scan triggered and polled to completion.
 
**Evidence:**
 
![QR-03 Phase 2 scan completion result](proof/phase2scan.png)
 
**Result:** p(90) completion time **25.1s** against a target of <30s - **passes**.
 
---
 
## Scalability
 
### QR-04 - System stability at 100 concurrent users
 
**Objective:** Validate that the system remains stable as concurrent users ramp up to 100.
 
**Tool used:** k6
 
**Test performed:** `tests/k6/load_test.js`, `scalability` scenario - ramping virtual users from 0 to 100 over 3 stages (30s up / 1m sustained / 30s down) against `GET /api/v1/health`.
 
**Evidence:**
 
![QR-04 scalability test result](proof/Load+scalibiltytest.png)
 
**Result:** Error rate at peak load **0.00%** (0 failed out of 108,264 requests, up to 110 VUs) against a target of <50% degradation vs. baseline - thresholds held under load. **Caveat:** this run does not isolate a clean baseline measurement to compute degradation against (the `performance` and `scalability` scenarios executed concurrently), so the "<50% degradation vs. baseline" figure is not yet directly measured. This run also only proves the **API/HTTP layer** stays responsive (`GET /api/v1/health` never touches RabbitMQ/Celery) - it does not yet demonstrate the "horizontal worker scaling + queue-based load leveling" tactic, which would need a scenario against `POST /api/v1/scans/` with the rate limiter temporarily raised for the test.
 
---
 
## Reliability
 
### QR-05 - Crash rate on third-party OSINT API failure
 
**Objective:** Validate that the system recovers from third-party OSINT API failure without crashing.
 
**Tool used:** k6
 
**Test performed:** `tests/k6/phase1_scan_completion_test.js` (same run used for QR-02) - crash rate measured as the proportion of triggered scans that returned an unhandled error rather than a terminal status (`completed`/`partial`/`failed`). A dedicated script, `tests/k6/reliability_crash_rate_test.js`, also exists for this QR specifically (explicit crash-rate threshold rather than reading it off console logs).
 
**Evidence:**
 
![QR-05 reliability test result](proof/scan_crash.png)
 
**Result:** **0% crash rate (0/10)** against a target of <1% - **passes**. Every scan reached a terminal status; no unhandled errors. 10/10 runs returned `"partial"` status, consistent with expected graceful degradation under real OSINT conditions.
 
---
 
### QR-06 - Availability / uptime
 
**Objective:** Validate that the system maintains target uptime.
 
**Tool used:** UptimeRobot
 
**Test performed:**  UptimeRobot monitor configured against the deployed system.
 
**Evidence:** 
![QR-06 uptime](proof/uptimerobot.png)
 
**Result:** Target ≥99% / 99%.
 
---
 
## Security
 
### QR-07 - Medium+ risk alerts on staging
 
**Objective:** Validate that the system has no medium-or-above vulnerabilities, and that sensitive data is encrypted at rest.
 
**Tool used:** OWASP ZAP
 
**Test performed:** OWASP ZAP automated vulnerability scan against staging.
 
**Evidence:**
 
![QR-07 ZAP scan result](proof/zap_scan.png)
 
 
**Result:** **2 medium+ alerts found** against a target of 0 - . Alerts not yet triaged/fixed.
 
---
 
### QR-08 - Auth enforcement (401 / 404)
 
**Objective:** Validate that unauthenticated and cross-user requests are correctly rejected.
 
**Tool used:** k6
 
**Test performed:** `tests/k6/security_test.js` - checks an unauthenticated request to `GET /api/v1/domains` returns 401, and that an anonymous request for another user's scan status returns 404 (not 403 - ownership is enforced by a user_id-scoped lookup, not an explicit role check).
 
**Evidence:**
 
![QR-08 auth enforcement test result](proof/security.png)
 
**Result:** 401 **confirmed**, 0 secrets leaked in the response body. 404 cross-user check still **pending** - needs a real `AUTH_TOKEN` to create an owned scan first (see script comments).
 
---
 
### QR-09 - Secret exposure / rate limiting
 
**Objective:** Validate that no sensitive data is exposed in API responses, and that scan submission is rate-limited per IP.
 
**Tool used:** k6
 
**Test performed:** `tests/k6/security_test.js` - checks that the 4th `POST /api/v1/scans/` from the same IP within 10 minutes returns 429, and that none of the tested responses leak secrets/credentials/stack traces.
 
**Evidence:**
 
![QR-09 rate limiting test result](proof/security.png)
 
 
**Result:** **Confirmed** - 4th `POST /api/v1/scans/` from the same IP returned 429, no secrets leaked in the response body.
 
---
 
## Maintainability
 
### QR-10 - Zero lint errors on merged PRs
 
**Objective:** Validate that merged code passes static analysis with zero linting errors.
 
**Tool used:** ESLint (frontend) / ruff (backend + workers)
 
**Test performed:** `pnpm lint` - runs frontend ESLint and backend/workers ruff.
 
**Evidence:**
 
![QR-10 lint result](proof/lint.png)
 
 
**Result:** **0 errors** - `pnpm lint` passes clean. Some non-blocking `react-hooks/exhaustive-deps` warnings remain, but 0 errors.
 
---
 
### QR-11 - Test coverage threshold
 
**Objective:** Validate that backend and worker modules meet the automated test coverage target.
 
**Tool used:** pytest-cov
 
**Test performed:** `pytest` with coverage (`backend/pytest.ini`, `workers/pytest.ini`), run across backend + workers, unit + integration, merged via Codecov.
 
**Evidence:**
 
![QR-11 coverage result](proof/coverage.png)
 
**Result:** **64.5%** combined backend + workers coverage against a target of ≥80% - .
 
---
 
## Usability
 
### QR-12 - Accessibility score
 
**Objective:** Validate that primary user-facing pages are accessible.
 
**Tool used:** Google Lighthouse
 
**Test performed:** Lighthouse accessibility audit against the primary user-facing pages (dashboard, scan results).
 
**Evidence:**
 
![QR-12 Lighthouse result](proof/googelighthouse.png)
 
**Result:** **≥80** against a target of ≥80 - **passes**.
