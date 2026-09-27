import os
from typing import Any

import httpx

from app.services.rag.embedding_provider import EmbeddingProviderError


class EmbeddingServiceError(EmbeddingProviderError):
    pass


class EmbeddingService:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        )
        self.base_url = os.getenv(
            "OPENAI_BASE_URL",
            "https://api.openai.com/v1",
        ).rstrip("/")

        self.timeout = float(
            os.getenv("OPENAI_TIMEOUT_SECONDS", "30")
        )

        if not self.api_key:
            raise EmbeddingServiceError(
                "OPENAI_API_KEY is not configured.",
            )


    async def request_embeddings(
            self,
            texts: list[str],
    ) -> list[list[float]]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "input": texts,
                        "encoding_format": "float",
                    },
                )

                response.raise_for_status()

        except httpx.TimeoutException as exc:
            raise EmbeddingServiceError(
                "The embedding provider timed out.",
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise EmbeddingServiceError(
                "The embedding provider rejected the request.",
            ) from exc

        except httpx.RequestError as exc:
            raise EmbeddingServiceError(
                "The embedding provider is unavailable.",
            ) from exc

        payload: dict[str, Any] = response.json()
        data = payload.get("data")

        if not isinstance(data, list):
            raise EmbeddingServiceError(
                "The embedding provider returned an invalid response.",
            )

        ordered: dict[int, list[float]] = {}

        for item in data:
            if not isinstance(item, dict):
                raise EmbeddingServiceError(
                    "The embedding provider returned invalid embedding data.",
                )

            index = item.get("index")
            embedding = item.get("embedding")

            if not isinstance(index, int) or not isinstance(embedding, list):
                raise EmbeddingServiceError(
                    "The embedding provider returned invalid embedding data.",
                )

            ordered[index] = [
                float(value)
                for value in embedding
            ]

        if set(ordered) != set(range(len(texts))):
            raise EmbeddingServiceError("The embedding response did not match the request.")

        return [
            ordered[index]
            for index in range(len(texts))
        ]


    async def embed_batch(
            self,
            texts: list[str],
    ) -> list[list[float]]:
        normalized = [text.strip() for text in texts]

        if not normalized:
            return []

        if any(not text for text in normalized):
            raise EmbeddingServiceError(
                "Embedding inputs cannot be empty.",
            )

        embeddings: list[list[float]] = []

        batch_size = 100

        for start in range(0, len(normalized), batch_size):
            batch = normalized[start: start + batch_size]
            batch_embeddings = await self.request_embeddings(batch)
            embeddings.extend(batch_embeddings)

        return embeddings


    async def embed(self, text: str) -> list[float]:
        embeddings = await self.embed_batch([text])
        return embeddings[0]
