import os

from app.services.rag.bedrock_generation_provider import (
    BedrockGenerationProvider,
)
from app.services.rag.generation_provider import (
    GenerationProvider,
    GenerationProviderError,
)


def create_generation_provider() -> GenerationProvider:
    provider_name = os.getenv(
        "GENERATION_PROVIDER",
        "bedrock",
    ).strip().lower()

    if provider_name == "bedrock":
        return BedrockGenerationProvider()

    raise GenerationProviderError(
        f"Unsupported generation provider: {provider_name}"
    )
