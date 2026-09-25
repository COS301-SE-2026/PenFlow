import uuid 
from sqlalchemy.ext.asyncio import AsyncSession 

from app.models.verified_domain import VerifiedDomain 
from app.models.brand_intelligence import BrandMonitoring, BrandCandidate, BrandCandidateStatus 
from app.repositories.brand_intelligence_repository import BrandIntelligenceRepository
from app.schemas.brand_intelligence import BrandIngestionPayload 
from app.queue.celery_app import celery_app 

class BrandIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.repo = BrandIntelligenceRepository(db)
        self.db = db 

    async def trigger_monitoring_run(self, verified_domain_id: uuid.UUID, user_id: str) -> BrandMonitoring:
        domain_record = await self.db.get(VerifiedDomain, verified_domain_id)
        if not domain_record:
            raise ValueError("Verified domain not found")

        if domain_record.status != "verified":
            raise ValueError("Domain is not fully verified")

        if str(domain_record.user_id) != user_id:
            raise PermissionError("You do not have permission to scan this domain")

        monitor = await self.repo.create_or_activate_monitoring(verified_domain_id)

        celery_app.send_task(
            "brand.monitor_domain",
            args=[str(monitor.id), domain_record.domain],
        )

        return monitor 

    async def ingest_worker_results(self, payload: BrandIngestionPayload) -> None:
        monitor = await self.db.get(BrandMonitoring, payload.brand_monitoring_id)
        if not monitor:
            raise ValueError("Monitoring record not found")

        if not monitor.is_active:
            raise ValueError("Monitoring is currently inactive")

        await self.repo.upsert_candidates(payload.brand_monitoring_id, payload.candidates)
        await self.repo.update_run_timestamp(payload.brand_monitoring_id)

    async def update_status(
        self, candidate_id: uuid.UUID, status: BrandCandidateStatus, user_id: str
    ) -> BrandCandidate:
        candidate = await self.db.get(BrandCandidate, candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")

        monitor = await self .db.get(BrandMonitoring, candidate.brand_monitoring_id)
        domain_record = await self.db.get(VerifiedDomain, monitor.verified_domain_id)

        if str(domain_record.user_id) != user_id:
            raise PermissionError("You do not have permission to update this candidate")

        updated_candidate = await self.repo.update_candidate_status(candidate_id, status)
        return candidate 

    async def get_monitoring_overview(self, verified_domain_id: uuid.UUID, user_id: str) -> BrandMonitoring | None:
        domain_record = await self.db.get(VerifiedDomain, verified_domain_id)

        if domain_record and str(domain_record.user_id) != user_id:
            raise PermissionError("You do not have permission to view this domain")
        
        return await self.repo.get_monitoring_by_domain_id(verified_domain_id)