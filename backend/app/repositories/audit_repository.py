from uuid import UUID

from sqlalchemy import String, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.audit_log import AuditLog
from app.models.engagement import Engagement

class AuditRepository:
    @staticmethod
    async def list_for_engagement(
        db: AsyncSession,
        engagement_id: UUID,
        related_entity_ids: list[UUID] | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        conditions: list[ColumnElement[bool]] = [
            (AuditLog.entity_type == "engagement") & (AuditLog.entity_id == engagement_id)
        ]

        if related_entity_ids:
            conditions.append(AuditLog.entity_id.in_(related_entity_ids))

        query = (
            select(AuditLog).where(
                or_(*conditions)
            ).order_by(
                AuditLog.created_at.desc(),
                AuditLog.id.desc(),
            ).limit(limit)
        )

        result = await db.execute(query)
        return list(result.scalars().all())


    @staticmethod
    async def create_log(
        db: AsyncSession,
        *,
        user_id: UUID | None,
        action: str,
        entity_type: str,
        entity_id: UUID | None,
        metadata: dict[str, object] | None = None,
    ) -> AuditLog:
        rec = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_=metadata or {},
        )

        db.add(rec)
        await db.commit()
        await db.refresh(rec)

        return rec


    @staticmethod
    async def list_for_service_delivery(
        db: AsyncSession,
        service_delivery_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        engagement_ids = (
            select(Engagement.id)
            .where(Engagement.service_delivery_id == service_delivery_id)
        )

        query = (
            select(AuditLog)
            .where(
                or_(
                    (AuditLog.entity_type == "engagement") &
                    (AuditLog.entity_id.in_(engagement_ids))
                ),
                AuditLog.metadata_["engagement_id"].astext.in_(
                    select(Engagement.id.cast(String))
                    .where(Engagement.service_delivery_id == service_delivery_id)
                ),
            )
        ).order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        ).limit(limit).offset(offset)

        result = await db.execute(query)
        return list(result.scalars().all())