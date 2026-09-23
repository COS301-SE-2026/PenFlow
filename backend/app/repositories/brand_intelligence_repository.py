import uuid 
from datetime import datetime, timezone 
from typing import Sequence 
from sqlalchemy import select, update 
from sqlalchemy.orm import Session, selectinload

from app.models.brand_intelligence import BrandMonitoring, BrandCandidate, BrandCandidateStatus 
from app.schemas.brand_intelligence import BrandCandidateIngestItem 

class BrandIntelligenceRepository:
    def __init__(self, db: Session):
        self.db = db 

    def get_monitoring_by_domain_id(self, verified_domain_id: uuid.UUID) -> BrandMonitoring | None:
        query = (
            select(BrandMonitoring)
            .where(BrandMonitoring.verified_domain_id == verified_domain_id)
            .options(selectinload(BrandMonitoring.candidates))
        )
        return self.db.execute(query).scalar_one_or_none() 

    def get_monitoring_by_id(self, monitoring_id: uuid.UUID) -> BrandMonitoring | None:
        query = (
            select(BrandMonitoring)
            .where(BrandMonitoring.id == monitoring_id)
            .options(selectinload(BrandMonitoring.candidates))
        )
        return self.db.execute(query).scalar_one_or_none()

    def create_or_activate_monitoring(self, verified_domain_id: uuid.UUID) -> BrandMonitoring:
        existing = self.get_monitoring_by_domain_id(verified_domain_id)
        if existing:
            existing.is_active = True 
            self.db.commit()
            self.db.refresh(existing)
            return existing 

        new_monitor = BrandMonitoring(verified_domain_id=verified_domain_id, is_active=True)
        self.db.add(new_monitor)
        self.db.commit() 
        self.db.refresh(new_monitor)
        return new_monitor 

    def update_run_timestamp(self, monitoring_id: uuid.UUID) -> None:
        stmt = (
            update(BrandMonitoring)
            .where(BrandMonitoring.id == monitoring_id)
            .values(last_run_at=datetime.now(timezone.utc))
        )
        self.db.execute(stmt)
        self.db.commit()

    def upsert_candidates(
        self, monitoring_id: uuid.UUID, items: list[BrandCandidateIngestItem]
        ) -> list[BrandCandidate]:
        now = datetime.now(timezone.utc)
        persisted: list[BrandCandidate] = []

        for item in items:
            stmt = select(BrandCandidate).where(
                BrandCandidate.brand_monitoring_id == monitoring_id,
                BrandCandidate.normalized_domain == item.normalized_domain,
            )
            existing = self.db.execute(stmt).scalar_one_or_none()

            if existing:
                existing.last_seen = now 
                existing.risk_score = item.risk_score 
                existing.risk_level = item.risk_level 
                existing.evidence = item.evidence 
                persisted.append(existing)
            else:
                new_candidate = BrandCandidate(
                    brand_monitoring_id=monitoring_id, 
                    candidate_domain=item.candidate_domain,
                    normalized_domain=item.normalized_domain,
                    risk_score=item.risk_score, 
                    risk_level=item.risk_level, 
                    status=BrandCandidateStatus.NEW, 
                    evidence=item.evidence, 
                    first_seen=now,
                    last_seen=now,
                )
                self.db.add(new_candidate)
                persisted.append(new_candidate)

        self.db.commit()
        return persisted 

    def update_candidate_status(
        self, candidate_id: uuid.UUID, status: BrandCandidateStatus
    ) -> BrandCandidate | None:
        candidate = self.db.get(BrandCandidate, candidate_id)
        if not candidate:
            return None

        candidate.status = status
        if status == BrandCandidateStatus.RESOLVED:
            candidate.resolved_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(candidate)
        return candidate