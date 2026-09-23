import asyncio
import json
import os
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.services.rag.embedding_provider import EmbeddingProviderError


class BedrockEmbeddingProviderError(EmbeddingProviderError):
    pass


class BedrockEmbeddingProvider:
    SUPPORTED_DIMENSIONS = {256, 512, 1024}

    def __init__(self) -> None:
        self.region = os.getenv(
            "BEDROCK_REGION",
            "",
        ).strip()

        self.model_id = os.getenv(
            "BEDROCK_EMBEDDING_MODEL_ID",
            "amazon.titan-embed-text-v2:0",
        ).strip()

        dimensions_value = os.getenv(
            "BEDROCK_EMBEDDING_DIMENSIONS",
            "1024",
        )

        if not self.region:
            raise BedrockEmbeddingProviderError(
                "BEDROCK_REGION is not configured."
            )

        if not self.model_id:
            raise BedrockEmbeddingProviderError(
                "BEDROCK_EMBEDDING_MODEL_ID is not configured."
            )

        try:
            self.dimensions = int(dimensions_value)

        except ValueError as exc:
            raise BedrockEmbeddingProviderError(
                "BEDROCK_EMBEDDING_DIMENSIONS must be an integer."
            ) from exc

        if self.dimensions not in self.SUPPORTED_DIMENSIONS:
            raise BedrockEmbeddingProviderError(
                "BEDROCK_EMBEDDING_DIMENSIONS must be "
                "256, 512 or 1024."
            )

        self.model = (
            f"bedrock:{self.model_id}:{self.dimensions}"
        )

        try:
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
            )

        except BotoCoreError as exc:
            raise BedrockEmbeddingProviderError(
                "Amazon Bedrock could not be configured."
            ) from exc


    def request_embedding(
            self,
            text: str,
    ) -> list[float]:
        request_body = {
            "inputText": text,
            "dimensions": self.dimensions,
            "normalize": True,
        }

        try:
            response: dict[str, Any] = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )

        except (BotoCoreError, ClientError) as exc:
            raise BedrockEmbeddingProviderError(
                "Amazon Bedrock rejected the embedding request."
            ) from exc

        try:
            response_body = response["body"]
            payload = json.loads(response_body.read())

        except (
            KeyError,
            TypeError,
            UnicodeDecodeError,
            json.JSONDecodeError
        ) as exc:
            raise BedrockEmbeddingProviderError(
                "Amazon Bedrock returned an invalid response."
            ) from exc

        embedding = payload.get("embedding")

        if not isinstance(embedding, list):
            raise BedrockEmbeddingProviderError(
                "Amazon Bedrock returned no embedding."
            )

        if len(embedding) != self.dimensions:
            raise BedrockEmbeddingProviderError(
                "Amazon Bedrock returned an unexpected "
                "embedding dimension."
            )

        if any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            for value in embedding
        ):
            raise BedrockEmbeddingProviderError(
                "Amazon Bedrock returned invalid embedding values."
            )

        return [float(value) for value in embedding]


    async def embed_batch(
            self,
            texts: list[str],
    ) -> list[list[float]]:
        normalized = [
            text.strip()
            for text in texts
        ]

        if not normalized:
            return []

        if any(not text for text in normalized):
            raise BedrockEmbeddingProviderError(
                "Embedding inputs cannot be empty."
            )

        embeddings: list[list[float]] = []

        for text in normalized:
            embedding = await asyncio.to_thread(
                self.request_embedding,
                text,
            )
            embeddings.append(embedding)

        return embeddings


    async def embed(
            self,
            text: str,
    ) -> list[float]:
        embeddings = await self.embed_batch([text])
        return embeddings[0]