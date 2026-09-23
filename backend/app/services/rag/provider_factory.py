import os

from app.services.rag.bedrock_embedding_provider import (
    BedrockEmbeddingProvider,
)
from app.services.rag.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderError,
)
from app.services.rag.embedding_service import EmbeddingService


def create_embedding_provider() -> EmbeddingProvider:
    provider_name = os.getenv(
        "EMBEDDING_PROVIDER",
        "openai_compatible",
    ).strip().lower()

    if provider_name in {
        "openai",
        "openai_compatible",
        "ollama",
    }:
        return EmbeddingService()

    if provider_name == "bedrock":
        return BedrockEmbeddingProvider()

    raise EmbeddingProviderError(
        f"Unsupported embedding provider: {provider_name}"
    )