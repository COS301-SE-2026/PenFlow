from typing import Protocol


class EmbeddingProviderError(RuntimeError):
    pass


class EmbeddingProvider(Protocol):
    model: str

    async def embed_batch(
            self,
            texts: list[str],
    ) -> list[list[float]]:
        ...


    async def embed(
            self,
            text: str,
    ) -> list[float]:
        ...