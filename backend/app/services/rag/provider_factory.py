import os

from app.services.rag.bedrock_embedding_provider import (
    BedrockEmbeddingProvider,
)
from app.services.rag.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderError,
)
from app.services.rag.embedding_service import EmbeddingService
from app.services.rag.gemini_provider import GeminiEmbeddingProvider


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

    if provider_name == "gemini":
        return GeminiEmbeddingProvider()

    raise EmbeddingProviderError(
        f"Unsupported embedding provider: {provider_name}"
    )