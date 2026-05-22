# PenFlow — Software Architecture (Demo 1)



## 1. Architectural Overview

PenFlow is a cybersecurity platform that helps organizations progress from passive exposure discovery to deeper automated scanning and (later) managed engagements. For Demo 1, the architecture primarily supports:

- **Phase 1 CTEM (Passive OSINT Scan)**: asynchronous aggregation of multiple OSINT sources
- **Platform capabilities** required to make that scan practical: orchestration, state tracking, persistence, reporting

### 1.1 Architecture Style: Client–Server + Layered Modular Monolith

At a high level, PenFlow follows a **client–server** architecture:

- **Client:** Next.js web application (Presentation Layer)
- **Server:** FastAPI backend (Application / Domain Layer), PostgreSQL (Data Layer), asynchronous workers (Integration Layer)

PenFlow is implemented as a **Layered Modular Monolith** (n-tier) with strong separation of concerns. It is *not* microservices; instead, it is a single deployable system with internal modular boundaries.

### 1.2 Event-Driven / Asynchronous Extension

Long-running operations (OSINT scans, report generation, and later active scans) are implemented using an **event-driven + asynchronous task processing** model:

- API Gateway publishes tasks to a **RabbitMQ broker**
- **Celery workers** consume tasks independently
- **Redis** is used for fast state updates / pub-sub style events
- The UI receives progress updates (e.g., WebSockets) without blocking API request threads

This hybrid architecture provides responsive UX (fast HTTP responses) while supporting heavy background workflows.

---

## 2. Architecture Diagrams (Demo 1) — What They Mean in the Running System

This section embeds the core architectural diagrams and explains **what each diagram represents**, **why it matters**, and **how it maps to PenFlow’s runtime behavior**.

### 2.1 High-Level System Architecture
![High-Level Architecture](/docs/Architecture/images/Architecture%20Diagram.jpg)

**What this diagram shows**
- The full layered view: **Presentation → API Application Tier → Event Broker Tier → Async Service Tier → Data Tier**, plus external systems.
- The hybrid architecture: synchronous REST + asynchronous scan/report pipelines.

**How it works in PenFlow (Demo 1)**
- The Next.js client initiates a scan via REST to FastAPI.
- FastAPI validates input/auth (where applicable), creates scan records, and publishes scan work to RabbitMQ.
- Celery workers consume jobs, call external OSINT providers, normalize results, and persist them.
- Status transitions are written to Redis (and/or DB) and streamed back to the UI.

**Architectural requirements proven**
- Non-blocking scan execution (Performance)
- Fault tolerance through isolation and retries (Reliability)
- Modular monolith boundaries (Maintainability)

---

### 2.2 API Gateway (FastAPI) — Application Tier Detail
![API Gateway Diagram](/docs/Architecture/images/API%20Gateway%20Diagram.jpg)

**What this diagram shows**
- Internal decomposition of the FastAPI backend into layers/modules: routing/validation, middleware/auth, domain logic, state management, repository/data access.

**How it works in PenFlow (Demo 1)**
- Incoming requests go through request validation (Pydantic) and middleware (JWT verification where required).
- Domain logic orchestrates scan creation and task publishing.
- Repository layer isolates database details from orchestration logic.

**Architectural requirements proven**
- Input validation and sanitization (Security)
- Request routing isolation through modular routers (Maintainability)
- Automated API docs via OpenAPI/Swagger (Maintainability/Integrability)

---

### 2.3 Task Orchestration (RabbitMQ + Redis + Workers)
![Task Orchestration](/docs/Architecture/images/Task%20Orchestration.jpg)

**What this diagram shows**
- The asynchronous workflow: queue consumption, state changes, retry/backoff decisions, normalization, database commits.

**How it works in PenFlow (Demo 1)**
- Worker pulls a scan job from RabbitMQ.
- Worker updates scan status to “processing” (Redis/DB).
- Worker calls external OSINT APIs.
- If the API fails due to timeout/rate limit, the task is delayed/retried with exponential backoff.
- If successful, data is normalized and committed to PostgreSQL; status becomes “completed.”

**Architectural requirements proven**
- Fault tolerance (Reliability)
- Non-blocking work (Performance)
- Horizontal worker scaling (Scalability)

---

### 2.4 Celery Task Orchestration (Worker Execution Flow)
![Celery Task Orchestration](/docs/Architecture/images/Celery%20Task%20Orchestration.jpg)

**What this diagram shows**
- The worker-side orchestration: how Celery tasks are structured and how scan/report tasks can be chained or separated.

**How it works in PenFlow (Demo 1)**
- Celery provides routing + retries + durable background execution.
- Workers implement OSINT adapters and normalization logic.
- The system can add more worker containers to increase throughput without touching API capacity.

**Architectural requirements proven**
- Horizontal scalability
- Reliability via retry policies
- Maintainability via isolated adapters

---

### 2.5 Async OSINT Sequence Diagram (CTEM)
![Async OSINT SD](/docs/Architecture/images/Async%20OSINT%20SD.jpg)

**What this diagram shows**
- End-to-end message flow across the system from user interaction to persistent results.

**How it works in PenFlow (Demo 1)**
- User starts scan → UI calls API → API persists “pending” scan record → API enqueues scan job → returns 202 quickly.
- Worker pulls job → sets status = “processing” → status is pushed to UI.
- Worker queries external APIs → stores normalized results → sets status = “completed” → UI is notified → results can be retrieved.

**Architectural requirements proven**
- Responsiveness (API returns immediately)
- Real-time progress visibility (UX requirement)
- Clear separation between sync request and async execution

---

### 2.6 Deployment Diagram (Current Hosting Model)
![Deployment Diagram](/docs/Architecture/images/Deployment%20Diagram.jpg)

**What this diagram shows**
- Container layout and networking: Next.js, FastAPI, RabbitMQ, Redis, PostgreSQL, workers, and AWS services.

**How it works in PenFlow (Demo 1)**
- Next.js and FastAPI run in separate containers.
- RabbitMQ/Redis/Postgres are internal services in the same network.
- Reports/artifacts are stored in AWS S3; the API controls access.

**Architectural requirements proven**
- Isolation and segregation between components
- Clear runtime boundaries to support scaling
- Cloud storage separation for sensitive artifacts

---

### 2.7 Design Pattern Diagrams — How They Appear in PenFlow

#### Facade Pattern
![Facade](/docs/Architecture/images/Facade.jpg)

**How it maps to PenFlow**
- The FastAPI gateway acts as a façade for the client: it hides queueing, orchestration, retries, normalization, and persistence behind a small set of API endpoints.

#### Adapter Pattern
![Adapter](/docs/Architecture/images/Adapter.jpg)

**How it maps to PenFlow**
- Each OSINT provider integration is an adapter that converts unstable third-party JSON into a stable internal “finding contract.”

#### Observer Pattern
![Observer](/docs/Architecture/images/Observer.jpg)

**How it maps to PenFlow**
- State updates propagate from worker execution → Redis/state manager → WebSocket/UI updates. The UI reacts to status changes without polling.

---

## 3. Architectural Quality Requirements & Tactics (Demo 1)

This section defines the **architecturally significant requirements** and the **tactics** used to achieve them.

### 3.1 Scalability

**Requirement:**  
PenFlow must handle multiple concurrent scans and multiple concurrent users without degrading the responsiveness of the system.

**Tactics:**
- **Horizontal scaling of workers:** Celery worker processes/containers scale independently of the API.
- **Queue-based load leveling:** RabbitMQ absorbs bursts of scan requests so the system remains stable during spikes.
- **Stateless API instances (where possible):** Enables scale-out behind a load balancer/API gateway.

**Implications:**  
System throughput scales primarily by increasing worker capacity, not by increasing web server threads.

---

### 3.2 Performance (Responsiveness)

**Requirement:**  
User-facing operations must remain responsive even when scans are long-running or external services are slow.

**Tactics:**
- **Asynchronous task execution:** Scan logic runs off the request thread (via queue + workers).
- **Fast acknowledgement:** API returns quickly (e.g., `202 Accepted`) and provides a scan identifier for tracking.
- **Near-real-time progress updates:** UI is updated through event/state streaming (e.g., WebSockets) instead of polling.

**Target behavior (Demo 1):**
- API routes should typically respond within seconds, regardless of scan duration.
- The user should see incremental progress/status transitions for CTEM scans.

---

### 3.3 Reliability & Fault Tolerance

**Requirement:**  
PenFlow must continue producing usable results even when OSINT sources are unavailable, rate-limited, or intermittent.

**Tactics:**
- **Partial failure tolerance:** Individual OSINT adapter failures do not fail the entire scan.
- **Retry:** Worker tasks retry transient failures without cascading errors.
- **Timeouts and bounded calls:** External calls are bounded to prevent stuck scans.
- **Durable messaging:** RabbitMQ holds tasks until successfully consumed.

**Result:**  
PenFlow produces a “best-effort” report instead of failing hard due to a single upstream provider.

---

### 3.4 Maintainability & Evolvability

**Requirement:**  
PenFlow must support frequent change: adding/removing OSINT providers, adjusting normalized data structures, and refining report content without breaking the system.

**Tactics:**
- **Modular monolith boundaries:** Distinct modules (API/router layer, domain logic, adapters, persistence).
- **High cohesion / low coupling:** OSINT adapters are isolated behind stable interfaces/contracts.
- **Contract-based normalization:** Third-party output is mapped into a stable internal “finding contract.”
- **Strong typing + validation:** Pydantic models and mypy enforce early error detection.
- **Consistent quality gates:** Linting/formatting/testing in CI reduces long-term drift and regression risk.

---

### 3.5 Security (Core Requirement)

**Requirement:**  
PenFlow processes sensitive vulnerability and exposure data. The system must protect tenant data, credentials, and generated reports.

**Tactics:**
- **Authentication & Authorization:** JWT-based auth (Auth0) with role-based access control (RBAC).
- **Information hiding:** External API keys and internal scanning logic are not exposed to the client.
- **Transport security:** HTTPS/TLS for all client-server communication.
- **Least privilege (AWS IAM):** Roles/policies scoped to minimum required access.
- **Secure file delivery:** Reports stored in S3; access via controlled mechanisms (e.g., presigned URLs).

---

### 3.6 Observability (Operational Quality)

**Requirement:**  
The team must be able to debug scan failures and verify progress across asynchronous boundaries.

**Tactics:**
- **Centralized structured logging:** Correlate request IDs with scan IDs and Celery task IDs.
- **Audit-friendly scan state model:** Record state transitions consistently.
- **Metrics readiness:** Queue depth, task runtime, failure rate, retries.

---

## 4. Architectural Patterns (Demo 1)

### 4.1 Layered Architecture (n-tier)

PenFlow is structured as:

- **Presentation Layer:** Next.js UI
- **Application Layer (API Gateway):** FastAPI routers, validation, auth, orchestration
- **Domain Layer:** scan lifecycle and OSINT logic
- **Integration Layer:** adapters + worker workflows
- **Data Layer:** PostgreSQL, Redis, AWS S3

---

### 4.2 Event-Driven Architecture (EDA) for Long-Running Work

- “ScanRequested” → enqueued to broker
- “ScanInProgress”/“ScanSourceCompleted” → state updates in Redis/DB
- “ScanCompleted” → triggers report pipeline + UI updates

---

### 4.3 Repository Pattern (Data Access Isolation)

Database operations are isolated behind repositories to preserve separation of concerns and improve testability.

---

## 5. Design Patterns (Demo 1)

- **Facade:** API gateway hides subsystem complexity
- **Adapter:** OSINT provider integrations normalize data into internal contract
- **Observer:** real-time state updates from worker → UI
- **Repository:** isolates persistence
---

## 6. Architecture Constraints (Demo 1)

### 6.1 External Provider Constraints
- Rate limits and volatility from OSINT sources constrain scan throughput.

### 6.2 Network Volatility
- DNS, latency, TLS negotiation, and internet outages affect scan runtime.

### 6.3 Regulatory / Ethical Constraints
- Phase 1 scans remain passive (OSINT-only).
- Later phases require verification and strict scope enforcement.

### 6.4 Operational Constraints
- Architecture must remain manageable for a small team (modular monolith, clear boundaries).

### 6.5 AWS Cloud Constraints
- Artifacts stored in S3; access must be controlled via IAM and secure delivery patterns.

---

## 7. Architectural Responsibilities (Demo 1)

- **Next.js:** scan initiation UX + live status + results/report viewing
- **FastAPI:** validation/auth + orchestration + persistence + API surface
- **RabbitMQ/Celery:** background execution + retries + normalization
- **Redis:** scan state + real-time updates
- **PostgreSQL:** system of record (scans/findings/history)
- **S3:** report/artifact storage with controlled access

---

## 8. Appendix: Technology Stack (Demo 1)

- **Frontend:** Next.js (React) + TypeScript, Tailwind
- **Backend:** FastAPI (Python)
- **Async processing:** Celery
- **Broker:** RabbitMQ
- **State/cache:** Redis
- **Database:** PostgreSQL
- **Object storage:** AWS S3
- **Auth:** Auth0 (JWT, RBAC)
- **Containerization:** Docker / Compose
- **CI/CD:** GitHub Actions
- **Testing:** PyTest, Jest, Cypress
- **Code quality:** Ruff, ESLint, Prettier