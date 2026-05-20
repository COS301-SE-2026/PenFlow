# PenFlow

PenFlow is a distributed, pipeline-driven platform for managing the full penetration testing lifecycle, from passive reconnaissance to automated scanning and coordinated manual engagements.

## Phases
- Phase 1: Passive OSINT Scan (CTEM)
- Phase 2: Automated External Vulnerability Scan
- Phase 3: Manual Penetration Testing Workflow

## Tech Stack

### Frontend
- Next.js
- React (TypeScript)
- Tailwind CSS
- WebSockets (real-time scan progress updates)
-Jest
-ESLint
-Pretier

### Backend (Core API)
- FastAPI
- Python 3.12
- SQLAlchemy 
- Pydantic
- Alembic
- psycopg2
- Redis
- httpx
- WeasyPrint

### Workers & Scanning Engine
- Python (Celery)
- Redis (task queue & caching)
- SQLAlchemy
- httpx
- WeasyPrint
- Docker SDK
- Tenacity

### Database
- PostgreSQL 16

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
