<p align="center">
  <img 
    src="docs/images/logo-animated.gif" 
    width="360" 
    alt="PenFlow animated logo"
  />

<h1 align="center">PenFlow</h1>

<p align="center">
  <strong>Continuous Exposure → Automated Scanning → Managed Pentest Testing.</strong>
</p>

<p align="center">
  PenFlow is a cybersecurity platform that combines passive exposure monitoring,
  automated vulnerability scanning and managed penetration testing into a single
  continuous workflow.
</p>

<p align="center">
  <a href="https://pen-flow.com">
    <img
      alt="Live Platform"
      src="https://img.shields.io/badge/Live%20Platform-Open%20PenFlow-2980B9?style=flat&logo=googlechrome&logoColor=white"
    />
  </a>
  <a href="docs/SRS.md">
    <img
      alt="SRS"
      src="https://img.shields.io/badge/Documentation-SRS-555555?style=flat&logo=googledocs&logoColor=white"
    />
  </a>
  <a href="docs/SAS.md">
    <img
      alt="SAS"
      src="https://img.shields.io/badge/Documentation-SAS-555555?style=flat&logo=googledocs&logoColor=white"
    />
  </a>
  <a href="docs/User_Manual.pdf">
    <img
      alt="User Manual"
      src="https://img.shields.io/badge/Documentation-User%20Manual-555555?style=flat&logo=adobeacrobatreader&logoColor=white"
    />
  </a>
</p>

<p align="center">
  <a href="https://github.com/COS301-SE-2026/PenFlow/actions">
    <img alt="Build" src="https://img.shields.io/github/actions/workflow/status/COS301-SE-2026/PenFlow/ci.yml?branch=main&style=for-the-badge&logo=githubactions&logoColor=white" />
  </a>
  <a href="https://codecov.io/gh/COS301-SE-2026/PenFlow">
    <img alt="Coverage" src="https://img.shields.io/codecov/c/github/COS301-SE-2026/PenFlow?style=for-the-badge&logo=codecov&logoColor=white" />
  </a>
  <a href="https://stats.uptimerobot.com/bss8arWOgX">
    <img alt="Uptime" src="https://badge.uptimerobot.com/psp/e7b86e5f665e2ce069ae0d24b319156b.svg?style=logo&theme=dark" />
  </a>
  <a href="https://github.com/COS301-SE-2026/PenFlow/issues">
    <img alt="Issues" src="https://img.shields.io/github/issues/COS301-SE-2026/PenFlow?style=for-the-badge&logo=github&logoColor=white" />
  </a>
  <img alt="Demo 1" src="https://img.shields.io/badge/Demo%203-In%20Progress-2980B9?style=for-the-badge" />
</p>

<p align="center">
  <a href="https://readme-typing-svg.demolab.com">
    <img
      src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=14&duration=5000&pause=900&color=2980B9&center=true&vCenter=true&width=780&lines=Passive+CTEM+scans+without+blocking+your+API.;Queue-driven+scan+orchestration+with+Celery+%2B+RabbitMQ.;Progress+streamed+in+real+time+via+Redis+%2B+WebSockets."
      alt="Typing SVG"
    />
  </a>
</p>

---

## Overview

Traditional penetration testing workflows are fragmented across scanning tools, email threads, spreadsheets and static reports.

PenFlow Brings  these workflows into a single platform combining:

- Passive scan and exposure monitoring
- Automated external vulnerability scanning
- Domain ownership verification
- Managed Penetration testing engagements
- Findings, evidence and re-test tracking
- email-based coordination

PenFlow makes security posture **continuous** and **trackable** by structuring assessment into a phased pipeline.

---

## Platform Workflow

### Phase 1 — Passive CTEM

Passive reconnaissance and exposure discovery using external data sources
without directly touching or communicating with the target IPs.

- Passive OSINT aggregation
- Multiple sources queried asynchronously
- Normalized assets and findings
- Partial failure tolerant
- Risk scoring and reporting

### Phase 2 — Automated External Vulnerability Scan

Controlled active scanning against domains that have been verified by the
client.

- DNS-based domain ownership verification
- external vulnerability scanning
- worker-based scan orchestration
- finding normalization
- PDF report generation
- scan history

### Phase 3 — Manual Pentest Workflow

A workflow connecting clients, Service Delivery staff and
penetration testers.

- engagement requests and scoping
- pentester assignment and scheduling
- manual findings and evidence
- engagement messaging and notifications
- Service Delivery review
- re-tests and remediation tracking
- final report generation
- audit logging

---

## Architecture

PenFlow is a **layered modular monolith** with an **event-driven orchestration layer** workers for longer running scanning and reporting operations..

- **Frontend:** Next.js (TypeScript)
- **Core API:** FastAPI (Python)
- **Async Orchestration:** Celery + RabbitMQ
- **State/Updates:** Redis + WebSockets
- **Database:** PostgreSQL
- **Storage:** AWS S3
- **Auth:** Auth0 (JWT + RBAC)

### High-Level System Architecture

<div align="center">
    <img src="docs/Architecture/images/Architecture Diagram.jpg" alt="High-Level System Architecture" width="100%" style="border: 1px solid #444; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</div>

## Documentation

Detailed project documentation is available below.


| Document | Description |
| --- | --- |
| [Software Requirements Specification](docs/SRS.md)| Functional and non-functional requirements for PenFlow. |
| [Software Architecture Specification](docs/SAS.md) | Architecture, components, deployment, service contracts and design decisions. |
| [Design Specification](docs/DESIGN.md) | Detailed system and interface design documentation. |
| [Coding Standards](docs/coding_standards.md)| Instructions for using the PenFlow platform. |
| [User Manual](docs/User%20Manual.pdf) | Team development conventions and coding standards. |
| [Testing Policy](docs/Testingpolicy.md) | Testing strategy and team testing requirements. |
| [NFR Traceability Matrix](docs/NFR_Traceability_Matrix.md)| Mapping between non-functional requirements and their implementation/testing. |
| [NFR Testing](docs/NFRtesting.md)| Evidence and results for non-functional requirement testing. |

---

## Tech Stack

| Component      | Technology                       |
|----------------|----------------------------------|
| Frontend       | Next.js, React, TypeScript, Tailwind CSS |
| BAckend API    | FastAPI, Pydantic, SQLAlchemy, Alembic |
| Authentication | Keycloak, JWT, RBAC              |
| Workers        | Celery, httpx, Tenacity          |
| Broker / State | RabbitMQ                         |
| Database       | PostgreSQL 16                    |
| Storage        | AWS S3                           |
| CI/CD          | GitHub Actions                   |
| Testing        | PyTest, Jest, Cypress            |


---

<h2 align="center">Meet the Team — The BroCode</h2>

<table>
  <tr>
    <td align="center" valign="top" width="20%">
      <img src="docs/images/team/franky-liu.png" width="96" height="96" alt="Franky Liu" />
      <h3 style="margin:10px 0 4px 0;">Franky<br/>Liu</h3>
      <div><sub>Backend / Data</sub></div>
      <br/>
      <a href="https://github.com/24673898">
        <img alt="GitHub" src="https://img.shields.io/badge/GitHub-Profile-161A1D?style=flat-square&logo=github&logoColor=white" />
      </a>
      <br/>
      <a href="https://www.linkedin.com/in/franky-liu-83a2a8289/">
        <img alt="LinkedIn" src="https://img.shields.io/badge/LinkedIn-Profile-0A66C2?style=flat-square&logo=linkedin&logoColor=white" />
      </a>
    </td>
    <td align="center" valign="top" width="20%">
      <img src="docs/images/team/jeandre-opperman.png" width="96" height="96" alt="Jeandre Opperman" />
      <h3 style="margin:10px 0 4px 0;">Jeandre<br/>Opperman</h3>
      <div><sub>Backend / Integrations</sub></div>
      <br/>
      <a href="https://github.com/23542773">
        <img alt="GitHub" src="https://img.shields.io/badge/GitHub-Profile-161A1D?style=flat-square&logo=github&logoColor=white" />
      </a>
      <br/>
      <a href="https://www.linkedin.com/in/jeandre-opperman/">
        <img alt="LinkedIn" src="https://img.shields.io/badge/LinkedIn-Profile-0A66C2?style=flat-square&logo=linkedin&logoColor=white" />
      </a>
    </td>
    <td align="center" valign="top" width="20%">
      <img src="docs/images/team/aaron-kim.png" width="96" height="96" alt="Aaron Kim" />
      <h3 style="margin:10px 0 4px 0;">Aaron<br/>Kim</h3>
      <div><sub>Frontend / UI/UX</sub></div>
      <br/>
      <a href="https://github.com/Ronny-CS">
        <img alt="GitHub" src="https://img.shields.io/badge/GitHub-Profile-161A1D?style=flat-square&logo=github&logoColor=white" />
      </a>
      <br/>
      <a href="https://www.linkedin.com/in/aaron-kim-085414280/">
        <img alt="LinkedIn" src="https://img.shields.io/badge/LinkedIn-Profile-0A66C2?style=flat-square&logo=linkedin&logoColor=white" />
      </a>
    </td>
    <td align="center" valign="top" width="20%">
      <img src="docs/images/team/ayrtonn-taljaard.png" width="96" height="96" alt="Ayrtonn Taljaard" />
      <h3 style="margin:10px 0 4px 0;">Ayrtonn<br/>Taljaard</h3>
      <div><sub>Team Lead / Architecture</sub></div>
      <br/>
      <a href="https://github.com/AyrTal">
        <img alt="GitHub" src="https://img.shields.io/badge/GitHub-Profile-161A1D?style=flat-square&logo=github&logoColor=white" />
      </a>
      <br/>
      <a href="https://www.linkedin.com/in/ayrtonn-taljaard-421b323b5/">
        <img alt="LinkedIn" src="https://img.shields.io/badge/LinkedIn-Profile-0A66C2?style=flat-square&logo=linkedin&logoColor=white" />
      </a>
    </td>
    <td align="center" valign="top" width="20%">
      <img src="docs/images/team/damian-moustakis.png" width="96" height="96" alt="Damian Moustakis" />
      <h3 style="margin:10px 0 4px 0;">Damian<br/>Moustakis</h3>
      <div><sub>Systems / Security</sub></div>
      <br/>
      <a href="https://github.com/Locutus-0201">
        <img alt="GitHub" src="https://img.shields.io/badge/GitHub-Profile-161A1D?style=flat-square&logo=github&logoColor=white" />
      </a>
      <br/>
      <a href="https://www.linkedin.com/in/damian-moustakis-664727303/">
        <img alt="LinkedIn" src="https://img.shields.io/badge/LinkedIn-Profile-0A66C2?style=flat-square&logo=linkedin&logoColor=white" />
      </a>
    </td>
  </tr>
</table>

<p><b>Contact:</b> thebrocodetuks@gmail.com</p>
