# PenFlow 
# Software Architecture Specification (SAS)

## 1. Architectural Overview

PenFlow is a cybersecurity platform designed to help organisations understand their external attack surface by progressing from passive exposure discovery to active security scanning.

The project was originally developed around passive CTEM (Continuous Threat Exposure Management) principles, where information is gathered from publicly available sources without directly interacting with the target. During Phase 2 the architecture was extended to support active reconnaissance, allowing verified targets to be scanned using a distributed worker pipeline.

The architecture therefore supports two primary operational phases.

- **Phase 1 Passive CTEM**
  - Asynchronous aggregation of multiple OSINT providers.
  - Normalisation of collected intelligence.
  - Exposure discovery without directly interacting with target infrastructure.


- **Phase 2 Active Security Scanning**
  - Target verification and resolution.
  - Active network and web application scanning.
  - Technology fingerprinting.
  - Vulnerability correlation.
  - Normalised Findings and Assets.
  - Backend filtering and reporting.

---

### 1.1 Architectural Objectives

Several architectural goals guided the design of PenFlow throughout both development phases.

The architecture aims to:

- keep the user interface responsive while long-running scans execute
- separate presentation, business logic and persistence responsibilities
- support asynchronous execution of expensive operations
- allow scanning capabilities to evolve independently
- provide a consistent representation of discovered security information
- To reduce the coupling between major system components
- remain maintainable for a small development team

These objectives influenced many of the architectural decisions discussed throughout this specification.

---

### 1.2 Architecture Style: Client–Server + Layered Modular Monolith

At a high level, PenFlow follows a **client–server** architecture:

- **Client:** Next.js web application (Presentation Layer), which is responsible for all our user interactions.
- **Server:** FastAPI backend (Application / Domain Layer), PostgreSQL (Data Layer), asynchronous workers (Integration Layer)

PenFlow is implemented as a **Layered Modular Monolith** (n-tier), in the backend with strong separation of concerns. It is *not* microservices; instead, it is a single deployable system with internal modular boundaries.

The major architectural layers are:

- Presentation Layer
    - Next.js frontend


- Application Layer
    - FastAPI API Gateway
    - routing
    - validation
    - authentication
    - orchestration


- Domain Layer
    - business logic
    - scan lifecycle
    - reporting


- Integration Layer
    - Celery workers
    - RabbitMQ
    - external security tools
    - OSINT providers


- Data Layer
    - PostgreSQL
    - AWS S3

---

### 1.3 Event-Driven / Asynchronous Extension

PenFlow has many Long-running operations (OSINT scans, report generation, and active scans). They are implemented using an **event-driven + asynchronous task processing** model:

When long-running work is required we have: 

- The FastAPI API creates the scan record
- The task is published to RabbitMQ
- Celery workers consume the task
- progress and scan state are persisted to the database while asynchronous workers continue processing in the background
- the frontend receives status updates while processing continues in the background

This hybrid architecture provides responsive UX (fast HTTP responses) while supporting heavy background workflows.

---

### 1.4 Phase 2 Architectural Evolution

Phase 2 represents an architectural extension rather than a redesign.

Instead of introducing one large active scanner, the scanning pipeline was decomposed into a collection of specialised workers responsible for individual scanning responsibilities.

Examples include:

- Target Resolution
- Nmap
- HTTP Security
- TLS Analysis
- Technology Fingerprinting
- CPE Resolution
- CVE Correlation

Each worker performs one clearly defined responsibility before passing its results into the remainder of the pipeline.

This improves maintainability, reduces coupling between scanning components and allows new workers to be introduced with minimal impact on the rest of the architecture.

Every worker produces the same high-level output consisting of:

- Raw Results
- Findings
- Assets
- Status

Because every worker follows the same contract, downstream systems such as persistence, reporting and frontend filtering remain independent from the implementation details of individual workers.

The complete worker architecture is discussed in **Phase2-Worker-Architecture.md**, while the complete lifecycle of scan information is described in **Phase2-Data-Flow.md**.

---

## 2. Architecture Diagrams

This section embeds the core architectural diagrams and explains **what each diagram represents**, **why it matters**, and **how it maps to PenFlow’s runtime behavior**.

### 2.1 High-Level System Architecture
![High-Level Architecture](/docs/Architecture/images/Architecture%20Diagram.jpg)

**What this diagram shows**
- The full layered view: **Presentation → API Application Tier → Event Broker Tier → Async Service Tier → Data Tier**, plus external systems.
- The hybrid architecture: synchronous REST + asynchronous scan/report pipelines.

**How it works in PenFlow**
- The Next.js client initiates a scan via REST to FastAPI.
- FastAPI validates input/auth (where applicable), creates scan records, and publishes scan work to RabbitMQ.
- Celery workers consume jobs, call external OSINT providers, normalize results, and persist them.
- Status transitions are written to Redis (and/or DB) and streamed back to the UI.

**Architectural requirements proven**
- Non-blocking scan execution (Performance)
- Fault tolerance through isolation and retries (Reliability)
- Modular monolith boundaries (Maintainability)

---

### 2.2 API Gateway (FastAPI) - Application Tier Detail
![API Gateway Diagram](/docs/Architecture/images/API%20Gateway%20Diagram.jpg)

**What this diagram shows**
- Internal decomposition of the FastAPI backend into layers/modules: routing/validation, middleware/auth, domain logic, state management, repository/data access.

**How it works in PenFlow**
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

**How it works in PenFlow**
- Worker pulls a scan job from RabbitMQ.
- Worker updates scan status to “processing” (DB).
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

**How it works in PenFlow**
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

**How it works in PenFlow**
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

### 2.7 Design Pattern Diagrams - How They Appear in PenFlow

#### Facade Pattern
![Facade](/docs/Architecture/images/Facade.jpg)

**How it maps to PenFlow**
- The FastAPI gateway acts as a facade view for the client: it hides queueing, orchestration, retries, normalization, and persistence behind a small set of API endpoints.

#### Adapter Pattern
![Adapter](/docs/Architecture/images/Adapter.jpg)

**How it maps to PenFlow**
- Each OSINT provider integration is an adapter that converts unstable third-party JSON into a stable internal “finding contract.”

#### Observer Pattern
![Observer](/docs/Architecture/images/Observer.jpg)

**How it maps to PenFlow**
- State updates propagate from worker execution → Redis/state manager → WebSocket/UI updates. The UI reacts to status changes without polling.

---
### 2.8 Phase 2 Worker Architecture

Demo 2 introduces the first implementation of the Phase 2 worker pipeline.

Rather than implementing a single large security scanner, the architecture follows a pipeline of specialised workers, each responsible for one stage of the scan.

This decision follows the Single Responsibility Principle and improves maintainability by allowing workers to evolve independently.

Each worker produces a standardised output consisting of:

• Raw Results

• Findings

• Assets

• Status

Because every worker follows the same output contract, downstream systems such as reporting and frontend filtering remain independent of worker-specific implementations.

Additional implementation details are documented in Phase2-Worker-Architecture.md.

---

## 3. Deployment Architecture (Demo 2)

### 3.1 Deployment Overview

While Demo 1 focused primarily on the software architecture of PenFlow, Demo 2 introduced the deployment architecture used to host and operate the platform.

PenFlow is deployed using a containerised cloud architecture built on AWS services. The deployment separates application components into independent containers while maintaining a single logical application.

This approach provides several advantages:

- isolation between application components
- simplified deployment and updates
- horizontal scalability
- improved fault tolerance
- easier infrastructure management

The deployment architecture supports both the passive CTEM functionality introduced during Phase 1 and the active security scanning pipeline introduced during Phase 2.

---

### 3.2 Deployment Components

The current deployment architecture consists of the following major components.

| Component | Technology |
| --- | --- |
| Frontend | Next.js |
| Backend | FastAPI |
| Workers | Celery |
| Message Broker | RabbitMQ |
| Database | PostgreSQL (Amazon RDS) |
| Authentication | Keycloak |
| Object Storage | Amazon S3 |
| Containers | Docker |
| Container Hosting | Amazon ECS (Fargate) |
| Container Registry | Amazon ECR |

---

### 3.3 Deployment Characteristics

#### Containerisation

All major application components are packaged as Docker containers.

Containerisation provides a consistent execution environment across development, testing and production environments while simplifying deployment and maintenance.

---

#### Scalability

PenFlow separates the frontend, backend and worker services into independent deployment units.
This allows individual components to scale according to demand without requiring the entire application to scale simultaneously.

For example, additional worker instances can be deployed when scan volume increases without affecting frontend or backend capacity.

---

#### Reliability

The deployment architecture incorporates several mechanisms that improve reliability.

- Application Load Balancer health checks detect unhealthy services.
- Amazon ECS automatically replaces failed containers.
- RabbitMQ provides durable task queues for asynchronous processing.
- PostgreSQL provides persistent storage for application data.

These mechanisms help ensure that failures remain isolated and do not affect the entire platform.

---

#### Security

Several deployment decisions were made to support secure operation of the platform.

- HTTPS/TLS is used for client-server communication.
- Keycloak provides authentication and identity management.
- Secrets are stored using AWS Secrets Manager rather than within source code.
- IAM roles and security groups restrict infrastructure access according to least-privilege principles.
- Sensitive reports and artifacts are stored within Amazon S3.

---

#### Monitoring and Observability

Operational visibility is provided through Amazon CloudWatch.

Logs, metrics and service health information can be monitored to identify failures from there.

---

### 3.4 Relationship to Phase 2

The deployment architecture introduced during Demo 2 directly supports the Phase 2 worker pipeline.

The worker architecture described in **Phase2-Worker-Architecture.md** executes within the Celery worker tier, while the data lifecycle described in **Phase2-Data-Flow.md** is supported through RabbitMQ, PostgreSQL and the backend API.

The deployment architecture therefore acts as the infrastructure foundation upon which the Phase 2 scanning architecture operates.

---

### 3.5 Deployment Environments

PenFlow distinguishes between development and production environments.

| Environment | Infrastructure | Purpose |
| --- | --- | --- |
| Development | Docker Compose / local services | Local development and testing by team members |
| Production | AWS ECS, RDS, Amazon MQ, S3, ECR, ALB, Secrets Manager and CloudWatch | Publicly accessible deployment used for Demo 2 |

The development environment run the PenFlow services locally using Docker Compose, providing equivalent application components without requiring the AWS infrastructure.

The production environments is hosted on AWS and is publicly accessible at:

**https://pen-flow.com**

Authentication is provided through:

**https://auth.pen-flow.com**

The `main` branch is automatically deployed to the production environment after the PenFlow CI completes successfully.

---

### 3.6 Infrastructure as Code and Reproducibility

PenFlow's AWS infrastructure is defined using Terraform. Infrasturcutre definitions are stored within the repository under `infra/`, allowing the required cloud resources to be recreated from a script rather than manual configuration.

The Terraform configuration provides the required networking, ECS services & task definitions, Application Load Balancers, RDS database, Amazon MQ broker, etc.

A bootstrap script is provided to automate initial infrastructure deployment. During bootstrap, the required Docker images are built and pushed to Amazon ECR, the database schema and keycloak database are intialized, and the ECS application services are started.

Environment specific Terraform values are documented using `terraform.tfvars.example`, while sensitive values are supplied seperately and are not stored in version control.


#### Fresh Infrastructure Deployment

1. Clone the repository and configure `infra/terraform.tfvars` from `terraform.tfvars.example`.
2. Configure AWS CLI credentials and the required external API credentials.
3. Run `terraform init`, `terraform validate`, and `terraform plan`.
4. Run `./scripts/bootstrap-infra.sh` with the required database, Keycloak and RabbitMQ passwords.
5. Configure the generated DNS validation/application records.
6. Verify the frontend, backend and authentication health endpoints.

---

### 3.7 Secrets Management

Production runtime secrets, credentials and API keys are all stored in AWS Secrets Manager and supplied to ECS containers at runtime.

GitHub Actions uses GitHub repository secrets for values required by the deployment pipeline. AWS authentication from GitHub Actions uses OpenID Connect (OIDC), allowing the workflow to assume an AWS IAM deployment role with limited permissions without storing AWS access keys in the repository.

---

### 3.8 Continuous Integration and Deployment

PenFlow uses GitHub Actions for continuous integration and automated production deployment.

The CI workflow is triggered by pushes and pull requests targeting the configured development and main branches. The pipeline validates the frontend, backend and worker components through linting, type checking, unit testing and builds.

After these checks succeed, Docker images are built to verify containerisation. Integration tests and Docker health checks then verify communication between application components and supporting services.

A successful CI run associated with a push to the `main` branch triggers the production deployment workflow.

During production deployment:

1. The commit that passed CI is resolved and checked out.
2. GitHub Actions authenticates with AWS using OIDC.
3. Production Docker Images for the frontend, backend and workers are built.
4. Images are tagged using the deployment commit SHA and pushed to Amazon ECR.
5. New ECS task definition revisions are created using the new images.
6. The backend, workers and frontend ECS services are updated sequentially.
7. ECS service stability is verified.
8. Production smoke tests verify the frontend, backend API and Keycloak authentication endpoints.

A failure during any stage of the pipeline will cause the workflow to fail.

---

### 3.9 Deployment Artifacts

The primary production artifacts are Docker container images.

| Artifact | Produced By | Storage / Deployment Target |
| --- | --- | --- |
| Frontend Docker image | Production deployment workflow | Amazon ECR → ECS Frontend Service |
| Backend Docker image | Production deployment workflow | Amazon ECR → ECS Backend Service |
| Worker Docker image | Production deployment workflow | Amazon ECR → ECS Worker Service |
| Test coverage | CI workflows | Codecov |
| PenFlow database schema | Database bootstrap image | Amazon RDS PostgreSQL |
| Generated reports | Backend / workers | Amazon S3 |

Production container images are tagged using the first 12 characters of the Git commit SHA. This provides traceability between deployed artifacts.

---

### 3.10 Rollback Strategy

PenFlow production iamges are tagged using the Git commit SHA rather than relying solely on a mutable `latest` tag. ECS deployments create new task revisions referencing the corresponding image version.

If a deployment introduces a failure, the affected ECS service can be rolled back to its previous task definition revision, which references the previously deployed container image stored in Amazon ECR.

The rollback process therefore consists of:
1. Identify the last known stable ECS task definition revision.
2. Update the affected ECS service to use that revision.
3. Wait for ECS service stability.
4. Re-run the produciton health checks to verify recovery.

Because previous image versions remain available in Amazon ECR, rollback does not require rebuilding the previous application version.

---

### 3.11 Deployment Architecture

![Deployment Diagram](/docs/Architecture/images/Deployment-Diagram.jpg)

Client requests first pass through **Cloudflare DNS**, which manages domain resolution and routes traffic to the **AWS Application Load Balancer (ALB)**.
The Application Load Balancer distributes incoming requests to the appropriate application services hosted within **Amazon ECS**, where the **Next.js frontend** serves the user interface and the **FastAPI backend** processes API requests.
When a user initiates a long-running operation, such as an active vulnerability scan, the backend publishes the task to **RabbitMQ**. One or more **Celery workers** consume these tasks asynchronously, execute the required scanning operations, and persist the results to **Amazon RDS (PostgreSQL)**.
Generated reports and supporting artifacts are stored in **Amazon S3**, while completed scan results are retrieved through the backend and presented to users via the frontend.

The deployment diagram below illustrates these infrastructure components and their relationships.

---

### 3.12 CI/CD Pipeline Diagrams

![PenFlow CI](/docs/Architecture/images/PenFlow_CI.jpg)

![PenFlow Prod](/docs/Architecture/images/PenFlow_Prod.jpg)

## 4. Architectural Quality Requirements & Tactics

This section defines the **architecturally significant requirements** and the **tactics** used to achieve them.

--- 

### 4.1 Availability

PenFlow is expected to remain available even when individual application components fail.
To support this, the frontend, backend and worker services are deployed independently within Amazon ECS. Application Load Balancer health checks detect unhealthy services while ECS automatically replaces failed containers. RabbitMQ separates user requests from long-running scan execution, ensuring that temporary worker failures do not prevent users from interacting with the API.
As the platform grows, additional backend and worker instances can be deployed to further improve service availability by removing individual containers as single points of failure.

---

### 4.2 Scalability

**Requirement:**  
PenFlow must handle multiple concurrent scans and multiple concurrent users without degrading the responsiveness of the system, it was designed so we could scale the differing parts independently.
The frontend, backend and Celery worker sections are all deployed as separate components allowing for workers to be added without needing to make changes to the frontend and backend.

**Tactics:**
- **Horizontal scaling of workers:** Celery worker processes/containers scale independently of the API.
- **Queue-based load leveling:** RabbitMQ absorbs bursts of scan requests so the system remains stable during spikes.
- **Stateless API instances (where possible):** Enables scale-out behind a load balancer/API gateway.

**Implications:**  
System throughput scales primarily by increasing worker capacity, not by increasing web server threads.

**Phase2:**
Phase 2 further reinforces this by decomposing scanning into multiple independent workers. Individual workers can be paralleled or replaced without affecting the remainder of the pipeline, allowing future expansion and or additions to our worker frameworks.

---

### 4.3 Performance (Responsiveness)

**Requirement:**  
User-facing operations must remain responsive even when scans are long-running or external services are slow.

**Tactics:**
- **Asynchronous task execution:** Scan logic runs off the request thread (via queue + workers).
- **Fast acknowledgement:** API returns quickly (e.g., 202 Accepted) and provides a scan identifier for tracking.
- **Near real-time progress updates:** UI is updated through event/state streaming (e.g., WebSockets) instead of polling.

**Target behavior (Demo 1):**
- API routes should typically respond within seconds, regardless of scan duration.
- The user should see incremental progress/status transitions for CTEM scans.

---

### 4.4 Reliability & Fault Tolerance

**Requirement:**  
PenFlow must continue producing usable results even when OSINT sources are unavailable, rate-limited, or intermittent.
If workers fail, they remain isolated from the API through our task queue, this prevents any singular failing worker from harming the reliability of the rest of the pipeline.

**Tactics:**
- **Partial failure tolerance:** Individual OSINT adapter failures do not fail the entire scan.
- **Retry:** Worker tasks retry transient failures without cascading errors.
- **Timeouts and bounded calls:** External calls are bounded to prevent stuck scans.
- **Durable messaging:** RabbitMQ holds tasks until successfully consumed.

**Result:**  
PenFlow produces a “best-effort” report instead of failing hard due to a single upstream provider, The philosophy we used for PenFlow is to accept any usable data over no data at all from any given scan.

---

### 4.5 Maintainability & Evolvability

**Requirement:**  
PenFlow must support frequent change: adding/removing OSINT providers, adjusting normalized data structures, and refining report content without breaking the system.

**Tactics:**
- **Modular monolith boundaries:** Distinct modules (API/router layer, domain logic, adapters, persistence).
- **High cohesion / low coupling:** OSINT adapters are isolated behind stable interfaces/contracts.
- **Contract-based normalization:** Third-party output is mapped into a stable internal “finding contract.”
- **Strong typing + validation:** Pydantic models and mypy enforce early error detection.
- **Consistent quality gates:** Linting/formatting/testing in CI reduces long-term drift and regression risk.
- **Standardised Outputs:** Standardised worker output further improves maintainability by ensuring that all downstream components consume a common data structure

---

### 4.6 Security (Core Requirement)

**Requirement:**  
PenFlow processes sensitive vulnerability and exposure data. The system must protect tenant data, credentials, and generated reports.

**Tactics:**
- **Authentication & Authorization:** JWT-based auth (Auth0) with role-based access control (RBAC).
- **Information hiding:** External API keys and internal scanning logic are not exposed to the client.
- **Transport security:** HTTPS/TLS for all client-server communication.
- **Least privilege (AWS IAM):** Roles/policies scoped to minimum required access.
- **Secure file delivery:** Reports stored in S3; access via controlled mechanisms (e.g., presigned URLs).

As a cybersecurity platform, security forms a fundamental part of our architectural requirement.
Authentication is handled through: 
- **Keycloak**
- **HTTPS/TLS**
- **AWS Secrets Manager**

Both Keycloak and The HTTPS/TLS protocols are our way of ensuring a safe environment while AWS Secrets manager is our way of ensure the safety of information outside our internal system.
Infrastructure components are further protected using IAM roles and security groups, while generated reports and other persistent artifacts are stored within Amazon S3.
These architectural decisions help protect both application infrastructure and user data.


---

### 4.7 Observability (Operational Quality)

**Requirement:**  
The team must be able to debug scan failures and verify progress across asynchronous boundaries.

**Tactics:**
- **Centralized structured logging:** Correlate request IDs with scan IDs and Celery task IDs.
- **Audit-friendly scan state model:** Record state transitions consistently.
- **Metrics readiness:** Queue depth, task runtime, failure rate, retries.

---

### 4.8 Quality Requirement Mapping

The following table summarises how the architectural decisions made throughout PenFlow support the quality requirements identified in the Software Requirements Specification.

| Quality Requirement | Architectural Decision                                                                                                                                                                                                                                  |
|---------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Performance | Long-running scans are executed asynchronously using RabbitMQ and Celery workers, allowing the FastAPI backend to respond immediately while scan processing continues in the background.                                                                |
| Reliability | RabbitMQ provides durable task queues while Celery supports retry mechanisms for failures. Worker failures are isolated from the API, allowing scans to finish with partial results where possible.                                                     |
| Scalability | The frontend, backend and worker services are deployed as independent components. Additional worker instances can be introduced without affecting the remainder of the application, while RabbitMQ buffers scan requests during periods of high demand. |
| Security | Keycloak provides authentication and identity management, HTTPS/TLS secures client communication, AWS Secrets Manager protects sensitive credentials, and IAM roles restrict infrastructure access according to least-privilege principles.             |
| Maintainability | PenFlow follows a layered modular architecture and decomposes Phase 2 scanning into specialised workers that communicate through a common data contract, allowing new scanning capabilities to be introduced with minimal architectural changes.        |
---

## 5. Architectural Patterns

PenFlow combines several architectural patterns to satisfy the functional and quality requirements within our project.
Rather than relying on a single architectural style, the system combines a layered modular monolith with asynchronous event-driven processing. 

Together these patterns provide:
- **Separation of Concerns**
- **Maintainability**
- **Scalability**
- **Support for long-running scanning operations**

The following sections describe the primary architectural patterns adopted throughout the platform.

### 5.1 Layered Architecture (n-tier)

PenFlow is structured as primarily a layered monolith:
Our Responsibilities are mainly separated into 5 distinct layers:

- **Presentation Layer:** Next.js Frontend responsible for all user interactions.
- **Application Layer (API Gateway):** FastAPI routers, validation, auth, orchestration
- **Domain Layer:** business logic for scan lifecycles, OSINT logic and reporting and vulnerability processing.
- **Integration Layer:** Celery workers, RabbitMQ orchestrator and OSINT providers.
- **Data Layer:** PostgreSQL for persistent storage in our DB, Amazon S3 for report and artifact storage for client and business use.

Our layered approach allows us to modify and change workers independently without disrupting the standardised output and flow we have designed.

---

### 5.2 Event-Driven Architecture
Long-Running scans are developed using the premise of an event-driven architecture
Our data flow is orchestrated so the backend publishes scans to RabbitMQ that are then consumed by the Celery Workers.

The typical workflow looks like this:

- **ScanRequested** - published by FastAPI
- **WorkerStarted** - Celery worker begins processing
- **WorkerCompleted** - findings persisted
- **ScanCompleted** - frontend updated

---

### 5.3 Repository Pattern (Data Access Isolation)

PenFlow separates persistence logic from business logic through the Repository Pattern.
Database operations are encapsulated within repository classes responsible for interacting with PostgreSQL, Thus workers dont need to directly write to the DB and the backend can take the responsibility for the action.

This provides several benefits:

- **Reduced coupling between business logic and persistence**
- **Simplified testing**
- **Easier database maintenance**
- **Improved code reuse**

The repository abstraction also ensures that our future database changes will have minimal impact on higher application layers.

---

### 5.4 Worker Pipeline Architecture (Phase 2)

The Phase 2 vulnerability scanning system follows a pipeline architecture built around specialised scanning workers.
Rather than implementing one monolithic vulnerability scanner, the scanning process is separated into multiple  async workers.

The Pipeline stages include:

- **Target Resolution**
- **Nmap ports and services enumeration**
- **HTTP Security Analysis**
- **TLS Analysis**
- **Technology Fingerprinting**
- **CPE Resolution**
- **CVE Correlation**

Each worker consumes the output produced by previous stages before generating a standardised result consisting of:

- **Raw Results**
- **Findings**
- **Assets**
- **Status**

Because every worker follows the same data contract, With this we can add many more workers without needing to change other backend/ frontend related architecture.
This pipeline architecture significantly improves extensibility and our scalability.

---

## 6. Design Patterns

PenFlow makes use of design patterns to improve our modularity and maintainability. These patterns help us add new features while not having to change much of the architecture to do it.

## 6.1 Facade Pattern

- **Facade:** FastAPI gateway hides subsystem complexity so as to not expose it to the frontend user interface. The gateway coordinates the underlying components on the users behalf.

---

## 6.2 Adapter Pattern

- **Adapter:** We employ multiple OSINT providers and security tools, each of whichs results are normalized to confirm with a set data contract.

---

## 6.3 Observer Pattern

- **Observer:** real-time state updates to show progress to users. As the workers are executed, their various stages are sent to the frontend, allowing for the users to efficiently monitor progress.

---

## 6.4 Repository Pattern

- **Repository:** DB access is encapsulated within repository classes to isolate the persistence and business logic sections from one another.
- The repo pattern also allowed us to provide an interface for storing the data in our subsequent sections; findings, assets, assets and reports while hiding the direct db access.

---

## 6.5 Pipes and Filter pattern (Phase 2)

**Pipeline:** The phase 2 workers follow a pipeline where the scan is broken into a sequence of specialised workers responsible for their individual fields. 

- **Target Resolution**
- **Port Scanning**
- **HTTP security scanning**
- **TLS analysis**
- **Tech stack fingerprinting**
- **Cpe generation**
- **CVE correlations**

By standardising outputs into our common fields(findings, assets , etc..)New scanning stages can be introduced without much impact to the rest of the pipeline.

---

## 7. Architecture Constraints

The following constraints influenced our design and way of implementing the PenFlow architecture.

### 7.1 Technology Constraints

The project architecture is constrained by these technologies.

- The backend is implemented using **FastAPI**.
- The frontend is implemented using **Next.js**.
- Background processing is implemented using **Celery workers**.
- **RabbitMQ** is used as the message broker for asynchronous task execution.
- **PostgreSQL** is used as the relational database.
- **Docker containers** are used to provide consistent execution environments.

---

### 7.2 External Provider Constraints

PenFlow relies on numerous third-party services and public data sources:
- **Shodan**
- **Hunter.io**
- **HaveIBeenPwned**
- **crt.sh**
- **Wappalyzer**
- **CVE NVD queries**

With these services the following constraints were introduced:
- **API rate Limiting**
- **Service Availability**
- **Response time**
- **Response Reliability**
- **Differing Response Formats**

---

### 7.3 Regulatory / Ethical Constraints

- Phase 1 scans remain passive (OSINT-only).
- Phase 2 Introduced Domain Verification and more direct scans which could be deemed invasive, For navigating this we needed to endure we properly rate limited so as to not ddos Domains by accident.

---

### 7.4 Operational Constraints

- Architecture must remain manageable for a small team (modular monolith, clear boundaries).

---

### 7.5 Worker Pipeline Constraints (Phase 2)

The Phase 2 scanning architecture follows a fixed processing pipeline.
Certain workers depend on information produced by earlier stages of the scan. For Example the Cpe resolver and CVE queries only work if we in the fingerprinting section come up with a technology used and or version.
As a result, worker execution must respect the logical ordering of the pipeline while maintaining the standardised Findings and Assets data contract between each of our workers.

---

### 7.6 Deployment Constraints

The production deployment targets a containerised cloud environment.
Application components are deployed as Docker containers hosted within AWS servers, with RabbitMQ, PostgreSQL and supporting services.
The architecture thus assumes reliable communication between distributed containers.

---

### 7.7 Team Constraints

PenFlow was developed by a small student development team within fixed academic deadlines, Those being various demo timelines separated through the academic year.
To reduce implementation complexity and simplify maintenance, the project adopts a layered modular monolith rather than a microservices architecture while still supporting asynchronous background processing through specialised workers, This was all in the aid of having members work on sections individually to produce workable units we later integrated together as a team

---

## 8. Architectural Responsibilities

| Component | Architectural Responsibility                                                                                                                                                 |
|-----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Next.js Frontend** | Provides the user interface, initiates scans, displays scan progress, presents findings, reports and historical scan data and acts as a lohin/singup medium.                 |
| **FastAPI Backend** | Exposes the REST API, validates requests, manages authentication and authorisation, orchestrates scan workflows, persists application data and coordinates worker execution. |
| **RabbitMQ** | Provides asynchronous message delivery between the backend and worker services, enabling long-running tasks to execute independently of user requests.                       |
| **Celery Workers** | Execute asynchronous scanning tasks, perform security analysis, normalise results and produce the standard Findings and Assets data contract.                                |
| **PostgreSQL** | Serves as the primary persistent data store for users, scans, findings, assets, reports and audit information.                                                               |
| **Keycloak** | Manages user authentication, identity management and access control.                                                                                                         |
| **Amazon S3** | Stores generated reports and other application artefacts for secure retrieval.                                                                                               |
| **Docker & Amazon ECS** | Provide container orchestration and runtime environments for deploying and scaling application components.                                                                   |

---

## 9. Technology Stack

The technologies selected for PenFlow were chosen to support the architectural objectives described throughout this specification.

| Technology | Architectural Role |
|------------|--------------------|
| **Next.js** | Implements the presentation layer and provides the web-based user interface. |
| **FastAPI** | Implements the application layer, exposing REST APIs and coordinating business logic. |
| **Celery** | Executes asynchronous background tasks, enabling long-running scans without blocking user requests. |
| **RabbitMQ** | Provides reliable message-based communication between the backend and worker services. |
| **PostgreSQL** | Stores persistent application data, including scans, findings, assets and user information. |
| **Keycloak** | Provides authentication, identity management and role-based access control. |
| **Amazon S3** | Stores generated reports and other persistent artefacts. |
| **Docker** | Packages application components into portable, reproducible execution environments. |
| **Amazon ECS (Fargate)** | Hosts and manages containerised application services in the production environment. |
| **Amazon ECR** | Stores container images used during deployment. |
| **Cloudflare DNS** | Provides domain management and request routing to the deployed application. |
| **AWS Application Load Balancer** | Distributes incoming requests across application services and performs health checks. |

---

---

## 10. Supporting Architecture Documents

The Software Architecture Specification provides the high-level architectural decisions that guide the design of PenFlow.

The following supporting documents provide additional detail for the Phase 2 architecture introduced during Demo 2.

| Document                                                                        | Purpose                                                                                                                                                      |
|---------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [Phase 2 Worker Architecture](/docs/Architecture/phase2-worker-architecture.md) | Describes the worker pipeline, worker responsibilities, the standard worker contract, and architectural rationale for the distributed scanning architecture. |
| [Phase 2 Data Flow](/docs/Architecture/phase2-data-flow.md)                     | Describes how scan information flows through the backend, workers, Findings, Assets and reporting pipeline.                                                  |


---

## Service Contracts

The PenFlow system exposes REST-based service contracts between the frontend, backend, worker services, and supporting infrastructure. Each contract defines the HTTP endpoint, accepted inputs, authentication requirements, expected response structure, and error behaviour. Internal callback endpoints are also documented because they form explicit communication boundaries between the asynchronouos work subsystem and the backend.

### 1: Domain Verification Service

The Domain Verification Service allows authenticated users to register domains, verify domain ownership, and remove domains that are no longer required.

---

#### 1.1: Add Domain for Verification

**Endpoint** `POST /api/v1/domains/`

**Purpose**
Registers a domain against the authenticated user and creates a domain verification record. The backend generates the information required for the subsequent ownership-verification process.

**Authentication**
Required. The authenticated user's provider identifier is obtained from the authentication token and mapped to the corresponding PenFlow user.

**Request Body**

```json
{
    "domain": "hackerone.com"
}
```

| Field | Type | Required | Description |
|---|---|---:|---|
| `domain` | string | Yes | Domain that the user wishes to register for verification. |

**Success Response: `201 Created`**

Returns a `VerifiedDomainResponse` describing the newly registered domain and its current verification state.

Example:


```json
{
    "id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
    "domain": "hackerone.com",
    "status": "pending",
    "verification_token": "penflow-verification=pentoken123...",
    "verified_at": null
}
```

**Error Responses:**

- `401 Unauthorized`: The authenticated identity does not correspond to a PenFlow user.
- `409 Conflict`: The authenticated user has already registered the supplied domain.
- `422 Unprocessable Entity`: The request body is invalid or the supplied domain cannot be normalised into a valid non-empty domain.

---

#### 1.2: Verify Domain Ownership

**Endpoint** `POST /api/v1/domains/{domain_id}/verify`

**Purpose**  
Checks the DNS TXT records of a previously registered domain for its issued verification token. If the expected token is found, the domain is marked as verified.

**Authentication**  
Required: The authenticated user may only verify a domain linked with their own account, and no others.

**Path Parameters**

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `domain_id` | UUID | Yes | Identifier of the domain verification record. |

**Request Body**  
None.

**Rate Limit**  
Maximum of 10 verification requests per minute per client IP address.

**Success Response: `200 OK`**

Returns the updated `VerifiedDomainResponse`.

```json
{
    "id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
    "domain": "hackerone.com",
    "status": "verified",
    "verification_token": "penflow-verification=pentoken123...",
    "verified_at": "2026-06-06T11:11:11Z"
}
```

If the domain has already been successfully verified, then existing verified record is returned. No new attempts would be needed.

**Error Responses**

- `400 Bad Request`: Domain verification failed.
  - the expected DNS TXT record could not be found;
  - a TXT record exists but the verification token does not match;
  - the DNS lookup could not be completed.
- `401 Unauthorized`: The authenticated identity does not correspond to a PenFlow user.
- `404 Not Found`: The domain record does not exist or is not associated with a registered user.
- `422 Unprocessable Entity`: The supplied `domain_id` is not a valid UUID.

---

#### 1.3: List Registered Domains

**Endpoint** `GET /api/v1/domains`

**Purpose**  
Returns the domain verification records belonging to the authenticated user. The endpoint supports status filtering, searching, sorting and pagination and also returns counts for each verification status.

**Authentication**  
Required. Only records belonging to the authenticated PenFlow user are returned.

**Query Parameters**

| Parameter | Type | Required | Default | Description                                               |
|---|---|---:|---|-----------------------------------------------------------|
| `status` | enum | No | None | Filter by domain verification status.                     |
| `search` | string | No | None | Search value. Maximum length is 255 characters.           |
| `sort` | enum | No | `created_at` | Sort field: `domain`, `created_at`, or `status`.          |
| `order` | enum | No | `desc` | Sort direction: `asc` or `desc`.                          |
| `limit` | integer | No | `20` | Maximum number of records to return. Range: 1-100.        |
| `offset` | integer | No | `0` | Number of matching records to skip. Must be 0 or greater. |

**Request Body**  
None.

**Success Response: `200 OK`**

Returns a `DomainList` containing the registered domains, verification-status counts and pagination information.

```json
{
    "items": [
        {
            "id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
            "domain": "hackerone.com",
            "status": "verified",
            "verification_method": "dns_txt",
            "verification_token": "penflow-verification=pentoken123...",
            "created_at": "2026-01-01T10:10:10Z",
            "verified_at":"2026-06-06T11:11:11Z",
            "last_checked_at": "2026-09-01T08:30:00Z",
            "last_verification_code": "verified"
        }
    ],
    "counts": {
        "all": 1,
        "pending": 0,
        "verified": 1,
        "failed": 0,
        "expired": 0
    },
    "pagination": {
        "total": 1,
        "limit": 20,
        "offset": 0,
        "has_more": false
    }
}
```

**Error Responses**

- `401 Unauthorized`: The authenticated identity does not correspond to a PenFlow user.
- `422 Unprocessable Entity`: One or more query parameters do not satisfy the required type, enumeration, length or range constraints.

---

#### 1.4: Delete Registered Domain

**Endpoint** `DELETE /api/v1/domains/{domain_id}`

**Purpose**  
Deletes a domain verification record belonging to the authenticated user.

**Authentication**  
Required. The authenticated user may only delete domain records associated with their own account and no other.

**Path Parameters**

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `domain_id` | UUID | Yes | Identifier of the domain verification record to delete. |

**Request Body**  
None.

**Success Response: `204 No Content`**

The domain verification record was successfully deleted. No response body is returned.

**Error Responses**

- `401 Unauthorized`: The authenticated identity does not correspond to a PenFlow user.
- `404 Not Found`: The specified domain record does not exist or is not associated with the authenticated user.
- `422 Unprocessable Entity`: The supplied `domain_id` is not a valid UUID.

---

### 2: System Health Service

The System Health Service provides a lightweight health check for the PenFlow API and its database connection.

---

#### 2.1: Get System Health

**Endpoint** `GET /api/v1/health`

**Purpose**  
Checks whether the PenFlow API is running and attempts a simple database query to determine the current database connection state.

**Authentication**  
Not required.

**Request Body**  
None.

**Success Response: `200 OK`**

Returns the API health state, API version and current database connection state.

```json
{
    "status": "ok",
    "api_version": "1.0.0",
    "database": "connected"
}
```

The `database` field may contain:

- `connected`: the database health query completed successfully.
- `disconnected`: the database health query failed.

A database connection failure is logged, but the health endpoint itself still returns `200 OK` with the db shown as `disconnected`.

---

### 3: User Service

The User Service provisions the authenticated Keycloak identity within PenFlow and returns the corresponding 
 user information.

---

#### 3.1: Get Current User

**Endpoint** `GET /api/v1/users/me`

**Purpose**  
Returns the PenFlow user associated with the currently authenticated identity. 

If no PenFlow user exists for the authenticated Keycloak identity, a new client user is created. 

If the user already exists, their stored email and full name are updated from the current authentication information.

**Authentication**  
Required.

**Request Body**  
None.

**Success Response: `200 OK`**

Returns the PenFlow user's identifier, email address and role.

```json
{
    "id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
    "email": "user@usermail.com",
    "role": "client"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string | PenFlow user identifier. |
| `email` | string | Email address associated with the identity. |
| `role` | string | Current PenFlow application role. |

Newly provisioned users are assigned the `client` role.

**Error Responses**

- `500 Internal Server Error`: The backend failed to retrieve the PenFlow user.

---

### 4. Scan Service

The Scan Service manages Phase 1 passive CTEM scans and Phase 2 active vulnerability scans. It handles starting scans and returning their history, progress, metrics, findings, assets, services and risk history.

---

#### 4.1 Initiate Scan

**Endpoint** `POST /api/v1/scans/`

**Purpose**
Starts a Phase 1 passive CTEM or Phase 2 active vulnerability scan and queues the relevant Celery Pipeline.

Passive scans can be started anonymously. Active scans require an authenticated user and a verified domain owner by the user.

**Authentication**  
Optional for passive CTEM scans.  
Required for any and all active vulnerability scans.

**Request Body**

```json
{
    "domain": "hackerone.com",
    "scan_type": "passive_ctem",
    "verified_domain_id": null,
    "email": "steve@penflow.com"
}
```

| Field | Type | Required | Default      | Description                                           |
|---|---|---:|--------------|-------------------------------------------------------|
| `domain` | string | Yes |              | Target domain to scan.                                |
| `scan_type` | enum | No | `passive_ctem` | Type of scan either `passive_ctem` or `active_vulnerability`. |
| `verified_domain_id` | UUID / null | No | `null`       | Verified domain record used for an active vulnerability scan. |
| `email` | email / null | No | `null`       | Optional email address for automated report delivery. |

For an `active_vulnerability` scan:

- `verified_domain_id` must be supplied;
- the user must be authenticated;
- the domain must be fully verified; and
- the supplied `domain` must match the verified domain record.

**Rate Limit**  
Maximum of 3 scan initiation requests per 10 minutes per client IP address.

**Success Response: `202 Accepted`**

```json
{
    "scan_id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
    "status": "queued"
}
```
**Error Responses**

- `400 Bad Request`: An active scan is missing a `verified_domain_id`, or the supplied domain does not match its verification record.
- `401 Unauthorized`: An active vulnerability scan was requested without an authenticated user.
- `403 Forbidden`: The requested domain is not fully verified for the authenticated user.
- `422 Unprocessable Entity`: The request body does not satisfy the required schema, for example an invalid scan type, UUID or email address.
- `500 Internal Server Error`: An unexpected error occurred while starting the scan.

---

#### 4.2 List Scans

**Endpoint** `GET /api/v1/scans/`

**Purpose**
Returns the authenticated users scan history. Newest first. Results can also be filtered by their scan status.

**Authentication**  
Required.

**Query Parameters**

| Parameter | Type | Required | Default | Description                                             |
|---|---|---:|---|---------------------------------------------------------|
| `scan_status` | enum | No | None | Filter scans by their current status.                   |
| `limit` | integer | No | `10` | Maximum number of scans returned. Range: 1-100.         |
| `offset` | integer | No | `0` | Number of matching scans to skip. Must be 0 or greater. |

Supported scan statuses are:

- `queued`
- `running`
- `completed`
- `failed`
- `partial`

**Success Response: `200 OK`**

```json
[
    {
        "id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
        "domain": "hackerone.com",
        "created_at": "2026-06-06T11:11:11Z",
        "status": "completed",
        "scan_type": "passive_ctem",
        "progress": 100,
        "total_findings": 8,
        "critical_count": 1,
        "high_count": 2,
        "medium_count": 3,
        "low_count": 2
    }
]
```
Only scans belonging to the authenticated user are returned.

**Error Responses**

- `404 Not Found`: The authenticated identity does not correspond to a PenFlow user.
- `422 Unprocessable Entity`: A supplied status or pagination parameter is invalid.
- `500 Internal Server Error`: The backend failed to retrieve the user's scan history.

---

#### 4.3 Get Scan Status

**Endpoint** `GET /api/v1/scans/{scan_id}/status`

**Purpose**  
Returns the current scan status, progress, source statuses and report status.

**Authentication**  
Optional.

Anonymous scans can be checked without authentication. User owned scans require a matching authenticated users.

**Path Parameters**

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `scan_id` | UUID | Yes | Identifier of the scan. |

**Success Response: `200 OK`**

```json
{
    "scan_id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
    "domain": "hackerone.com",
    "created_at": "2026-06-06T11:11:11Z",
    "scan_type": "passive_ctem",
    "status": "running",
    "progress": 50,
    "sources": [
        {
            "source_name": "dns",
            "status": "completed",
            "error_message": null
        },
        {
            "source_name": "shodan",
            "status": "running",
            "error_message": null
        }
    ],
    "report_status": null
}
```

The sources shown depend on the scan type. Sources with no type are set to `pending`

**Error Responses**

- `404 Not Found`: The scan does not exist, the authenticated user could not be resolved, or the scan belongs to another authenticated user.
- `422 Unprocessable Entity`: The supplied `scan_id` is not a valid UUID.

---

#### 4.4 Get Scan Summary

**Endpoint** `GET /api/v1/scans/{scan_id}/summary`

**Purpose**  
Returns the scan summary, severity counts, top findings, asset impact, source coverage and report status.

**Authentication**  
Not required by the current endpoint.

**Path Parameters**

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `scan_id` | UUID | Yes | Identifier of the scan. |

**Success Response: `200 OK`**

```json
{
    "scan_summary": {
        "id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
        "domain": "hackerone.com",
        "status": "completed",
        "progress": 100,
        "created_at": "2026-06-06T11:11:11Z",
        "started_at": "2026-06-06T11:12:00Z",
        "completed_at": "2026-06-06T11:20:00Z",
        "error_message": null
    },
    "risk_snapshot": {
        "total_findings": 8,
        "critical_count": 1,
        "high_count": 2,
        "medium_count": 3,
        "low_count": 2,
        "info_count": 0
    },
    "top_findings": [
        {
            "id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
            "severity": "high",
            "title": "Missing Security Header",
            "description": "A security header expected by the scanner was not identified.",
            "recommendation": "Configure the required response header.",
            "source": "http_security",
            "asset_identifier": "hackerone.com",
            "asset_type": "domain",
            "created_at": "2026-06-06T11:15:00Z"
        }
    ],
    "asset_impact": {
        "total_assets_scanned": 4,
        "affected_assets_count": 2,
        "asset_type_breakdown": [
            {
                "asset_type": "domain",
                "total_assets": 2,
                "affected_assets": 1
            }
        ],
        "top_affected_assets": []
    },
    "source_coverage": {
        "aggregate": {
            "sources_total": 6,
            "sources_completed": 6,
            "sources_failed": 0,
            "sources_partial": 0,
            "sources_skipped": 0
        },
        "sources": []
    },
    "report_status": null
}
```

Returns up to five top findings. Long descriptions and recommendations are shortened for the preview.

**Error Responses**

- `404 Not Found`: No scan exists with the supplied identifier.
- `422 Unprocessable Entity`: The supplied `scan_id` is not a valid UUID.

---

#### 4.5 Get Scan Metrics

**Endpoint** `GET /api/v1/scans/{scan_id}/metrics`

**Purpose**  
Returns the scan's risk score and counts for findings, assets, services and detected technologies.

**Authentication**  
Not required.

**Path Parameters**

| Parameter | Type | Required | Description             |
|---|---|---:|-------------------------|
| `scan_id` | UUID | Yes | Identifier of the scan. |

**Success Response: `200 OK`**

Example:
```json
{
    "risk_score": 69,
    "risk_level": "MEDIUM RISK",
    "findings": {
        "critical": 1,
        "high": 2,
        "medium": 2,
        "low": 4,
        "info": 1,
        "total": 10
    },
    "assets": {
        "total": 5,
        "domain": 1,
        "subdomain": 3,
        "ip": 1
    },
    "services": {
        "total": 4,
        "tcp": 4
    },
    "technologies": {
        "total": 3,
        "web_server": 1,
        "framework": 2
    }
}
```

The risk score is capped at 100 and is calculated from finding severity using the current weighting:

- Critical: 25 points
- High: 15 points
- Medium: 5 points
- Low: 1 point

Risk levels are:

- `HIGH RISK`: score of 70 or greater
- `MEDIUM RISK`: score from 40 to 69
- `LOW RISK`: score below 40

**Error Responses**

- `404 Not Found`: The scan does not exist.
- `422 Unprocessable Entity`: The supplied `scan_id` is not a valid UUID.

---

#### 4.6 Get Scan Findings

**Endpoint** `GET /api/v1/scans/{scan_id}/findings`

**Purpose**  
Returns findings for a scan with optional severity filtering and pagination.

**Authentication**  
Not required.

**Path Parameters**

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `scan_id` | UUID | Yes | Identifier of the scan. |

**Query Parameters**

| Parameter | Type | Required | Default | Description                              |
|---|---|---:|---|------------------------------------------|
| `severity` | string | No | None | Filters findings by severity.            |
| `limit` | integer | No | `10` | Maximum findings returned. Range: 1-100. |
| `offset` | integer | No | `0` | Number of findings to skip.              |

**Success Response: `200 OK`**

```json
[
    {
        "id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
        "title": "Missing Security Header",
        "cve_id": null,
        "severity": "high",
        "cvss_score": 7.5,
        "source": "http_security",
        "asset_identifier": "hackerone.com",
        "description": "The expected security header was not identified.",
        "recommendation": "Configure the recommended security header."
    }
]
```

Results are ordered from newest to oldest.

If the scan has no findings, the endpoint returns an empty list.

**Error Responses**

- `422 Unprocessable Entity`: The scan ID or pagination values are invalid.

---

#### 4.7 Get Scan Assets

**Endpoint** `GET /api/v1/scans/{scan_id}/assets`

**Purpose**  
Returns assets found during a scan and the number of findings linked to each asset.

**Authentication**  
Not required.

**Path Parameters**

| Parameter | Type | Required | Description             |
|---|---|---:|-------------------------|
| `scan_id` | UUID | Yes | Identifier of the scan. |

**Query Parameters**

| Parameter | Type | Required | Default | Description                            |
|---|---|---:|---|----------------------------------------|
| `limit` | integer | No | `10` | Maximum assets returned. Range: 1-100. |
| `offset` | integer | No | `0` | Number of assets to skip.              |

**Success Response: `200 OK`**

```json
[
    {
        "id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
        "identifier": "hackerone.com",
        "asset_type": "domain",
        "findings_count": 4
    }
]
```

Assets with the most findings are returned first.

If no assets are found, an empty list is returned.

**Error Responses**

- `422 Unprocessable Entity`: A path or pagination parameter is invalid.

---

#### 4.8 Get Findings Page

**Endpoint** `GET /api/v1/scans/{scan_id}/findings-page`

**Purpose**  
Returns findings for the Findings page, including filtering, searching, sorting and severity counts.

**Authentication**  
Not required.

**Path Parameters**

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `scan_id` | UUID | Yes | Identifier of the scan. |

**Query Parameters**

| Parameter | Type | Required | Default | Description                                                                            |
|---|---|---:|---|----------------------------------------------------------------------------------------|
| `severity` | string | No | None | Severity filter. `low_info` combines Low and Informational findings.                   |
| `search` | string | No | None | Case-insensitive search across finding title, description and asset identifier.        |
| `sort_by` | string | No | `severity` | Sorting mode. `severity`, `cvss`, or any other value which falls back to newest first. |
| `limit` | integer | No | `12` | Maximum findings returned. Range: 1-100.                                               |
| `offset` | integer | No | `0` | Number of findings to skip.                                                            |

**Success Response: `200 OK`**

```json
{
    "total": 8,
    "counts": {
        "critical": 1,
        "high": 2,
        "medium": 2,
        "low_info": 3,
        "total": 8
    },
    "items": [
        {
            "id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
            "title": "Missing Security Header",
            "severity": "high",
            "cvss_score": 7.5,
            "cve_id": null,
            "source": "http_security",
            "status": "open",
            "description": "The expected security header was not identified.",
            "recommendation": "Configure the required security header.",
            "asset_identifier": "hackerone.com",
            "asset_type": "domain",
            "evidence": {},
            "created_at": "2026-06-06T11:15:00Z"
        }
    ]
}
```

The severity counts include all findings in the scan, not just the current page.

**Error Responses**

- `422 Unprocessable Entity`: A supplied path, severity or pagination value is invalid.

---

#### 4.9 Get Assets Page

**Endpoint** `GET /api/v1/scans/{scan_id}/assets-page`

**Purpose**  
Returns assets for the Assets page with category counts, finding counts, filtering and sorting.

**Authentication**  
Not required.

**Path Parameters**

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `scan_id` | UUID | Yes | Identifier of the scan. |

**Query Parameters**

| Parameter | Type | Required | Default | Description                                                            |
|---|---|---:|---|------------------------------------------------------------------------|
| `asset_type` | string | No | None | Filters by asset type.                                                 |
| `severity` | string | No | None | Filters assets according to their highest associated finding severity. |
| `search` | string | No | None | Case-insensitive search against the asset identifier.                  |
| `sort_by` | string | No | `risk` | Sorting mode: `risk`, `findings`, or identifier ordering.              |
| `limit` | integer | No | `15` | Maximum assets returned. Range: 1-100.                                 |
| `offset` | integer | No | `0` | Number of matching assets to skip.                                     |

**Success Response: `200 OK`**

```json
{
    "total": 5,
    "counts": {
        "total": 5,
        "domains": 1,
        "ips": 1,
        "subdomains": 2,
        "urls": 1,
        "other": 0
    },
    "items": [
        {
            "id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
            "identifier": "hackerone.com",
            "asset_type": "Domain",
            "ip_address": "203.0.113.24",
            "severity": "High",
            "findings_count": 4,
            "status": "Active",
            "created_at": "2026-06-06T11:12:00Z"
        }
    ]
}
```

TThe asset summary categories are:

- domains
- IPs
- subdomains
- urls
- other


**Error Responses**

- `422 Unprocessable Entity`: A path or pagination parameter is invalid.

---

#### 4.10 Get Services Page

**Endpoint** `GET /api/v1/scans/{scan_id}/services-page`

**Purpose**  
Returns services found during a scan together with protocol and state counts.

**Authentication**  
Not required.

**Path Parameters**

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `scan_id` | UUID | Yes | Identifier of the scan. |

**Query Parameters**

| Parameter | Type | Required | Default | Description                                                               |
|---|---|---:|---|---------------------------------------------------------------------------|
| `protocol` | string | No | None | Protocol filter such as `TCP` or `UDP`.                                   |
| `search` | string | No | None | Searches service name, product, host and port.                            |
| `sort_by` | string | No | `open` | `port` sorts numerically by port; other values use newest-first ordering. |
| `limit` | integer | No | `15` | Maximum services returned. Range: 1-100.                                  |
| `offset` | integer | No | `0` | Number of services to skip.                                               |

**Success Response: `200 OK`**

```json
{
    "total": 3,
    "counts": {
        "total": 3,
        "tcp": 2,
        "udp": 1,
        "open": 2,
        "filtered": 1
    },
    "items": [
        {
            "id": "2ec29dfa-6839-43ba-a45a-32a31f25dbdb",
            "service_name": "https",
            "host": "203.0.113.24",
            "port": 443,
            "protocol": "TCP",
            "product": "nginx",
            "version": "1.24",
            "state": "Open",
            "risk_level": "Low",
            "asset_count": 1,
            "banner": "nginx",
            "created_at": "2026-06-06T11:13:00Z"
        }
    ]
}
```

`risk_level` uses the highest finding severity for the service's asset. If there are no findings, it defaults to `Low`.

**Error Responses**

- `422 Unprocessable Entity`: A path or pagination parameter is invalid.

---

#### 4.11 Get Risk History

**Endpoint** `GET /api/v1/scans/{scan_id}/risk-history`

**Purpose**  
Returns risk scores from completed scans of the same domain.

**Authentication**  
Not required.

**Path Parameters**

| Parameter | Type | Required | Description                                                          |
|---|---|---:|----------------------------------------------------------------------|
| `scan_id` | UUID | Yes | Scan used to determine the domain whose history should be retrieved. |

**Success Response: `200 OK`**

```json
[
    {
        "date": "Jun 06",
        "risk_score": 69,
        "total_findings": 8
    },
    {
        "date": "Jul 07",
        "risk_score": 44,
        "total_findings": 5
    }
]
```

Up to 10 completed scans are returned, ordered from oldest to newest.

If the scan does not exist or has no completed history, an empty list is returned.

**Error Responses**

- `422 Unprocessable Entity`: The supplied `scan_id` is not a valid UUID.

---

### 5. Scan Report Service

The Scan Report Service allows completed scan reports to be downloaded as PDF files or sent to an email address.

---

#### 5.1 Download Scan PDF

**Endpoint** `GET /api/v1/scans/{scan_id}/pdf`

**Purpose**  
Downloads the completed PDF report for a scan.

**Authentication**  
Not required.

**Path Parameters**

| Parameter | Type | Required | Description             |
|---|---|---:|-------------------------|
| `scan_id` | UUID | Yes | identifier of the scan. |

**Request Body**  
None.

**Success Response: `200 OK`**

Returns the generated report as a PDF file.

The downloaded file uses the name:

```text
PenFlow_Report_{scan_id}.pdf
```

Reports may be stored locally or in Amazon S3. The endpoint retrieves the report from the configured storage location before returning it.

**Error Responses**

- `400 Bad Request`: The report has not finished generating or does not have a PDF file available.
- `404 Not Found`: No report exists for the scan, or the stored report could not be retrieved.
- `422 Unprocessable Entity`: The supplied `scan_id` is not a valid UUID.

---

#### 5.2 Email Scan Report

**Endpoint** `POST /api/v1/scans/{scan_id}/email-report`

**Purpose**  
Sends a completed scan report to the supplied email address.

**Authentication**  
Not required.

**Path Parameters**

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `scan_id` | UUID | Yes | Identifier of the scan. |

**Request Body**

```json
{
    "email": "steve@penflow.com"
}
```

| Field | Type | Required | Description |
|---|---|---:|---|
| `email` | email | Yes | Email address the report will be sent to. |

**Rate Limit**  
Maximum of 2 email requests per minute per client IP address.

**Success Response: `200 OK`**

```json
{
    "message": "Report emailed successfully"
}
```

The email contains the generated PDF report as an attachment.

**Error Responses**

- `400 Bad Request`: The report has not finished generating or does not have a PDF file available.
- `404 Not Found`: The scan does not exist.
- `422 Unprocessable Entity`: The supplied `scan_id` or email address is invalid.

---