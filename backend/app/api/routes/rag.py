import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import require_user
from app.models.user import User
from app.schemas.rag import (
    RAGAskRequest,
    RAGAskResponse,
    RAGIndexResponse,
    RAGSearchRequest,
    RAGSearchResponse,
)
from app.services.rag.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderError,
)
from app.services.rag.generation_provider import (
    GenerationProvider,
    GenerationProviderError,
)
from app.services.rag.generation_provider_factory import (
    create_generation_provider,
)
from app.services.rag.provider_factory import (
    create_embedding_provider,
)
from app.services.rag.rag_service import RAGService
from app.services.scan_service import ScanService
from app.utils.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


def get_embedding_service() -> EmbeddingProvider:
    try:
        return create_embedding_provider()

    except EmbeddingProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service is not configured",
        ) from exc


def get_generation_provider() -> GenerationProvider:
    try:
        return create_generation_provider()

    except GenerationProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Generation service is not configured",
        ) from exc


@router.post(
    "/scans/{scan_id}/index",
    response_model=RAGIndexResponse,
)
async def index_scan(
    scan_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
    embedding_service: EmbeddingProvider = Depends(get_embedding_service),
) -> RAGIndexResponse:
    await ScanService.require_scan_access(
        db,
        scan_id=scan_id,
        user_id=user.id,
    )

    try:
        result = await RAGService.index_scan_findings(
            db,
            scan_id=scan_id,
            embedding_service=embedding_service,
        )

        return RAGIndexResponse(**result)

    except EmbeddingProviderError as exc:
        logger.exception(
            "Embedding failed while indexing scan %s",
            scan_id,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Finding indexing is temporarily unavailable.",
        ) from exc


@router.post(
    "/scans/{scan_id}/search",
    response_model=RAGSearchResponse,
)
async def search_scan(
    scan_id: UUID,
    request: RAGSearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
    embedding_service: EmbeddingProvider = Depends(get_embedding_service),
) -> RAGSearchResponse:
    await ScanService.require_scan_access(
        db,
        scan_id=scan_id,
        user_id=user.id,
    )

    try:
        results = await RAGService.search_scan(
            db,
            scan_id=scan_id,
            question=request.question,
            limit=request.limit,
            embedding_service=embedding_service,
        )

        return RAGSearchResponse(
            question=request.question,
            results=results,
        )

    except EmbeddingProviderError as exc:
        logger.exception(
            "Embedding failed while searching scan %s",
            scan_id,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Similarity search is temporarily unavailable.",
        ) from exc


@router.post(
    "/scans/{scan_id}/ask",
    response_model=RAGAskResponse,
) 
async def ask_scan(
    scan_id: UUID,
    request: RAGAskRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
    embedding_service: EmbeddingProvider = Depends(
        get_embedding_service,
    ),
    generation_provider: GenerationProvider = Depends(
        get_generation_provider,
    ),
) -> RAGAskResponse:
    await ScanService.require_scan_access(
        db,
        scan_id=scan_id,
        user_id=user.id,
    )

    try:
        return await RAGService.answer_question(
            db,
            scan_id=scan_id,
            question=request.question,
            limit=request.limit,
            embedding_service=embedding_service,
            generation_provider=generation_provider,
        )

    except (
        EmbeddingProviderError,
        GenerationProviderError,
    ) as exc:
        logger.exception(
            "Security analysis failed for scan %s",
            scan_id,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security analysis is temporarily unavailable.",
        ) from exc

    