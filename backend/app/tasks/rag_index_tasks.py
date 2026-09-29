import asyncio
import logging
import time
from asyncio import AbstractEventLoop
from typing import Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.queue.celery_app import celery_app
from app.repositories.rag_repository import RAGRepository
from app.services.rag.embedding_provider import EmbeddingProviderError
from app.services.rag.provider_factory import create_embedding_provider
from app.services.rag.rag_service import RAGService

logger = logging.getLogger(__name__)

def create_session() -> Any:
    from app.config.database import SessionLocal

    return SessionLocal()

task_loop: AbstractEventLoop | None = None


def get_task_loop() -> AbstractEventLoop:
    global task_loop

    if task_loop is None or task_loop.is_closed():
        task_loop = asyncio.new_event_loop()

    return task_loop


async def index_scan(
        scan_id: str,
) -> dict[str, int]:
    parsed_scan_id = UUID(scan_id)

    async with create_session() as db:
        try:
            embedding_provider = create_embedding_provider()

        except EmbeddingProviderError:
            await db.rollback()

            await RAGRepository.mark_scan_index_failed(
                db,
                parsed_scan_id,
                failure_reason="Embedding service is unavailable."
            )

            raise

        return await RAGService.index_scan_findings(
            db,
            scan_id=parsed_scan_id,
            embedding_service=embedding_provider,
        )


@celery_app.task(
    bind=True,
    name="rag.index_scan",
    autoretry_for=(
        EmbeddingProviderError,
        SQLAlchemyError,
    ),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def index_scan_task(
    task: Any,
    scan_id: str,
) -> dict[str, int]:
    started_at = time.perf_counter()
    loop = get_task_loop()

    try:
        result = loop.run_until_complete(
            index_scan(scan_id)
        )

    except (
        EmbeddingProviderError,
        SQLAlchemyError,
    ):
        duration_ms = int(
            (time.perf_counter() - started_at) * 1000
        )

        logger.exception(
            "RAG indexing task failed "
            "scan_id=%s duration_ms=%s",
            scan_id,
            duration_ms,
        )

        raise

    duration_ms = int(
        (time.perf_counter() - started_at) * 1000
    )

    logger.info(
        "RAG indexing task completed "
        "scan_id=%s duration_ms=%s "
        "total_findings=%s indexed=%s unchanged=%s",
        scan_id,
        duration_ms,
        result["total_findings"],
        result["indexed"],
        result["unchanged"],
    )

    return result