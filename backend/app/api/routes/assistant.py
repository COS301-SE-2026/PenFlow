import logging
from time import perf_counter

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import require_user
from app.api.middleware.rate_limiter import (
    get_authenticated_request_key,
    limiter,
)
from app.models.user import User
from app.schemas.assistant import (
    AssistantQueryRequest,
    AssistantQueryResponse,
)
from app.services.assistant_service import AssistantService
from app.services.rag.embedding_provider import EmbeddingProviderError
from app.services.rag.generation_provider import GenerationProviderError
from app.utils.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/assistant",
    tags=["Ask PenFlow"],
)


@router.post(
    "/query",
    response_model=AssistantQueryResponse,
)
@limiter.limit(
    "10/minute",
    key_func=get_authenticated_request_key,
)
async def query_assistant(
    request: Request,
    payload: AssistantQueryRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> AssistantQueryResponse:
    started_at = perf_counter()

    try:
        response = await AssistantService.answer(
            db,
            user=user,
            request=payload,
        )

        duration_ms = (
            perf_counter() - started_at
        ) * 1000

        logger.info(
            "ask_penflow outcome=success "
            "user_id=%s capability=%s security_intent=%s "
            "page=%s source_count=%s duration_ms=%.1f",
            user.id,
            response.capability.value,
            (
                response.security_intent.value
                if response.security_intent is not None
                else "none"
            ),
            payload.context.page.value,
            len(response.sources),
            duration_ms,
        )

        return response

    except (
        EmbeddingProviderError,
        GenerationProviderError,
    ) as exc:
        duration_ms = (
            perf_counter() - started_at
        ) * 1000

        logger.exception(
            "ask_penflow outcome=provider_failure "
            "user_id=%s page=%s duration_ms=%.1f",
            user.id,
            payload.context.page.value,
            duration_ms,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ask PenFlow is temporarily unavailable.",
        ) from exc