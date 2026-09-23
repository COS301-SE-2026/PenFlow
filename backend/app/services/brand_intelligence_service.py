import uuid 
from sqlalchemy.orm import Session 

from app.models.verified_domain import VerifiedDomain 
from app.models.brand_intelligence import BrandMonitoring, BrandCandidate, BrandCandidateStatus 
from app.repositories.brand_intelligence_repository import BrandIntelligenceRepository
from app.schemas.brand_intelligence import BrandIngestionPayload 
from app.queue.celery_app import celery_app 

class BrandIntelligenceService:
    def __init__(self, db: Session):
        self.repo = BrandIntelligenceRepository(db)
        self.db = db 

    def trigger_monitoring_run(self, verified_domain_id: uuid.UUID) -> BrandMonitoring:
        domain_record = self.db.get(VerifiedDomain, verified_domain_id)
        if not domain_record:
            raise ValueError("Verified domain not found")

        monitor = self.repo.create_or_activate_monitoring(verified_domain_id)

        celery_app.send_task(
            "brand.monitor_domain",
            args=[str(monitor.id), domain_record.domain],
        )

        return monitor 

    def ingest_worker_results(self, payload: BrandIngestionPayload) -> None:
        self.repo.upsert_candidates(payload.brand_monitoring_id, payload.candidates)
        self.repo.update_run_timestamp(payload.brand_monitoring_id)

    def update_status(
        self, candidate_id: uuid.UUID, status: BrandCandidateStatus
    ) -> BrandCandidate:
        candidate = self.repo.update_candidate_status(candidate_id, status)
        if not candidate:
            raise ValueError("Candidate not found")
        return candidate 

    def get_monitoring_overview(self, verified_domain_id: uuid.UUID) -> BrandMonitoring | None:
        return self.repo.get_monitoring_by_domain_id(verified_domain_id)