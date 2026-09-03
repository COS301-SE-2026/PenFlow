<p align="center">
  <img 
    src="docs/images/logo-animated.gif" 
    width="180" 
    alt="PenFlow animated logo"
    style="border-radius: 24px; overflow: hidden;"
  />

<h1 align="center">PenFlow</h1>

<p align="center">
  <strong>Continuous exposure → automated scanning → managed pentest workflow.</strong><br/>
  A layered modular monolith with event-driven orchestration for long-running scans.
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
  <img alt="Demo 1" src="https://img.shields.io/badge/Demo%201-In%20Progress-2980B9?style=for-the-badge" />
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

## The Problem

Traditional penetration testing workflows are fragmented:
- static PDF reports
- email-based coordination
- poor visibility into change over time
- high-friction onboarding for SMBs

PenFlow makes security posture **continuous** and **trackable** by structuring assessment into a phased pipeline.

---

## The Solution (Pipeline)

### Phase 1 — Passive CTEM (Demo 1 focus)
- Passive OSINT aggregation (no direct interaction with target)
- Multiple sources queried asynchronously
- Partial failure tolerant
- Results normalized into a consistent finding contract

### Phase 2 — Automated External Vulnerability Scan (planned)
- Ownership verification
- Controlled external perimeter scanning
- Containerized isolation per scan

### Phase 3 — Manual Pentest Workflow (planned)
- RBAC + audit logging
- Engagement dashboard
- Findings submitted and tracked in-platform

---

## Architecture

PenFlow is a **layered modular monolith** with an **event-driven orchestration layer** for long-running work.

- **Frontend:** Next.js (TypeScript)
- **Core API:** FastAPI (Python)
- **Async Orchestration:** Celery + RabbitMQ
- **State/Updates:** Redis + WebSockets
- **Database:** PostgreSQL
- **Storage:** AWS S3
- **Auth:** Auth0 (JWT + RBAC)

### High-Level System Architecture
<img src="docs/Architecture/images/Architecture Diagram.jpg" alt="High-Level System Architecture" width="100%" />

## Documentation

Detailed project documentation is available below.


| Document | Description |
| --- | --- |
| [Software Requirements Specification](docs/SRS.md)
| [Software Architecture Specification](docs/SAS.md) 
| [Design Specification](docs/DESIGN.md) 
| [Coding Standards](docs/coding_standards.md)
| [User Manual](docs/User%20Manual.pdf) 
| [Testing Policy](docs/Testingpolicy.md) 
| [Brand Style](docs/TESTING.md)

---

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind |
| API Gateway | FastAPI, Pydantic, SQLAlchemy, Alembic |
| Workers | Celery, httpx, Tenacity |
| Broker / State | RabbitMQ, Redis |
| Database | PostgreSQL 16 |
| Storage | AWS S3 |
| Auth | Auth0 (JWT + RBAC) |
| CI/CD | GitHub Actions |
| Testing | PyTest, Jest, Cypress |


---

<h2>Meet the Team — The BroCode</h2>

<table>
  <tr>
    <td align="center" valign="top" width="20%">
      <img src="docs/images/team/franky-liu.jpg" width="96" height="96" style="border-radius:50%; object-fit:cover;" alt="Franky Liu" />
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
      <img src="docs/images/team/jeandre-opperman.jpg" width="96" height="96" style="border-radius:50%; object-fit:cover;" alt="Jeandre Opperman" />
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
      <img src="docs/images/team/aaron-kim.jpg" width="96" height="96" style="border-radius:50%; object-fit:cover;" alt="Aaron Kim" />
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
      <img src="docs/images/team/ayrtonn-taljaard.jpg" width="96" height="96" style="border-radius:50%; object-fit:cover;" alt="Ayrtonn Taljaard" />
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
      <img src="docs/images/team/damian-moustakis.jpg" width="96" height="96" style="border-radius:50%; object-fit:cover;" alt="Damian Moustakis" />
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
