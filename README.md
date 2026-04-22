# PenFlow

PenFlow is a distributed, pipeline-driven platform for managing the full penetration testing lifecycle, from passive reconnaissance to automated scanning and coordinated manual engagements.

## Phases
- Phase 1: Passive OSINT Scan (CTEM)
- Phase 2: Automated External Vulnerability Scan
- Phase 3: Manual Penetration Testing Workflow

## Tech Stack

### Frontend
- React (TypeScript)
- Tailwind CSS
- WebSockets (real-time scan progress updates)

### Backend (Core API)
- Node.js (Express)

### Workers & Scanning Engine
- Python (Celery)
- Redis (task queue & caching)

### Database
- PostgreSQL (Supabase)

### Storage
- Supabase Storage (reports & evidence files)

### Authentication
- Auth0 (JWT-based authentication & RBAC)

### Infrastructure
- Docker (containerized scan isolation)
- Render (hosting)
- GitHub Actions (CI/CD)

### Testing
- Jest (backend)
- PyTest (workers)
- Cypress (end-to-end)

### Reporting
- ReportLab (automated PDF report generation)

## Team
The BroCode
