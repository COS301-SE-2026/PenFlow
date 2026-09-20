from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finding import Finding
from app.models.rag_chunk import RAGChunk


class RAGRepository:
    @staticmethod
    async def list_enriched_findings_for_scan(
        db: AsyncSession,
        scan_id: UUID, 
    ) -> list[Finding]:
        query = (
            select(Finding).options(
                selectinload(Finding.scan),
                selectinload(Finding.asset),
                selectinload(Finding.service),
            ).where(Finding.scan_id == scan_id).order_by(
                Finding.id,
            )
        )

        result = await db.execute(query)
        return list(result.scalars().all())


    @staticmethod
    async def list_chunks_for_scan(
        db: AsyncSession,
        scan_id: UUID,
    ) -> list[RAGChunk]:
        query = select(RAGChunk).where(
            RAGChunk.scan_id == scan_id,
        )

        result = await db.execute(query)
        return list(result.scalars().all())


    @staticmethod
    async def synchronize_chunks(
        db: AsyncSession,
        scan_id: UUID,
        rows: list[dict[str, Any]],
        current_finding_ids: list[UUID],
    ) -> None:
        try:
            if rows:
                stmt = insert(RAGChunk).values(rows)

                stmt = stmt.on_conflict_do_update(
                    index_elements=[RAGChunk.finding_id],
                    set_={
                        "scan_id": stmt.excluded.scan_id,
                        "content": stmt.excluded.content,
                        "content_hash": stmt.excluded.content_hash,
                        "embedding_model": stmt.excluded.embedding_model,
                        "embedding": stmt.excluded.embedding,
                        "updated_at": func.now(),
                    },
                )

                await db.execute(stmt)

            stale_stmt = delete(RAGChunk).where(
                RAGChunk.scan_id == scan_id,
            )

            if current_finding_ids:
                stale_stmt = stale_stmt.where(
                    RAGChunk.finding_id.notin_(
                        current_finding_ids,
                    )
                )

            await db.execute(stale_stmt)
            await db.commit()

        except Exception:
            await db.rollback()
            raise


    @staticmethod
    async def search_scan(
        db: AsyncSession,
        scan_id: UUID,
        embedding_model: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[tuple[RAGChunk, Finding, float]]:
        distance = RAGChunk.embedding.cosine_distance(
            query_embedding
        ).label("distance")

        query = (
            select(RAGChunk, Finding, distance).join(
                Finding,
                Finding.id == RAGChunk.finding_id,
            ).where(
                RAGChunk.scan_id == scan_id,
                RAGChunk.embedding_model == embedding_model,
            ).order_by(distance.asc()).limit(limit)
        )

        result = await db.execute(query)

        return [
            (row[0], row[1], float(row[2]))
            for row in result.all()
        ]


    @staticmethod
    async def search_scan_text(
        db: AsyncSession,
        scan_id: UUID,
        embedding_model: str,
        question: str,
        limit: int
    ) -> list[tuple[RAGChunk, Finding, float]]:
        document = func.to_tsvector(
            "english",
            RAGChunk.content,
        )
        text_query = func.websearch_to_tsquery(
            "english",
            question,
        )
        rank = func.ts_rank_cd(
            document,
            text_query,
        ).label("text_rank")

        stmt = (
            select(RAGChunk, Finding, rank).join(
                Finding,
                Finding.id == RAGChunk.finding_id,
            ).where(
                RAGChunk.scan_id == scan_id,
                RAGChunk.embedding_model == embedding_model,
                document.op("@@")(text_query),
            ).order_by(
                rank.desc(),
                RAGChunk.finding_id.asc(),
            ).limit(limit)
        )

        result = await db.execute(stmt)

        return [
            (
                row[0],
                row[1],
                float(row[2]),
            )
            for row in result.all()
        ]