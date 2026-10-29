import asyncio
import math
import os
import re
from typing import Any

import httpx

from app.services.ai_privacy import (
    EMBEDDING_PRIVACY_VERSION,
    AIPrivacyError,
    PrivacySession,
    embedding_text,
)
from app.services.rag.embedding_provider import EmbeddingProviderError
from app.services.rag.generation_provider import GenerationProviderError


class GeminiProviderError(GenerationProviderError, EmbeddingProviderError):
    pass


def integer_setting(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(os.getenv(name, str(default)))
        
    except ValueError:
        raise GeminiProviderError(
            f"{name} must be an integer."
        ) from None

    if not minimum <= value <= maximum:
        raise GeminiProviderError(
            f"{name} must be between {minimum} and {maximum}."
        )

    return value


class GeminiClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()

        if not self.api_key:
            raise GeminiProviderError(
                "GEMINI_API_KEY is not configured."
            )

        self.timeout = integer_setting(
            "GEMINI_TIMEOUT_SECONDS", 60, 1, 120
        )

    async def request(
        self,
        model: str,
        operation: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", model):
            raise GeminiProviderError(
                "Invalid Gemini model identifier."
            )

        url = (
            "https://generativelanguage.googleapis.com"
            f"/v1beta/models/{model}:{operation}"
        )

        try:
            async with asyncio.timeout(self.timeout):
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=False,
                    trust_env=False,
                ) as client:
                    response = await client.post(
                        url,
                        headers={"x-goog-api-key": self.api_key},
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

        except (TimeoutError, httpx.TimeoutException):
            raise GeminiProviderError(
                "Gemini request timed out."
            ) from None

        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            raise GeminiProviderError(
                f"Gemini rejected the request (HTTP {code})."
            ) from None

        except httpx.RequestError:
            raise GeminiProviderError(
                "Gemini is unavailable."
            ) from None

        except ValueError:
            raise GeminiProviderError(
                "Gemini returned invalid JSON."
            ) from None

        if not isinstance(data, dict):
            raise GeminiProviderError(
                "Gemini returned an invalid response."
            )

        return data


class GeminiGenerationProvider:
    def __init__(self) -> None:
        self.client = GeminiClient()

        self.model_id = os.getenv(
            "GEMINI_GENERATION_MODEL",
            "gemini-2.5-flash",
        ).strip()
        self.model = f"gemini:{self.model_id}"

        self.max_tokens = integer_setting(
            "GEMINI_MAX_OUTPUT_TOKENS", 2048, 1, 8192
        )
        self.thinking_budget = integer_setting(
            "GEMINI_THINKING_BUDGET", 0, 0, 4096
        )
        self.thinking_level = os.getenv(
            "GEMINI_THINKING_LEVEL", "low"
        ).strip()

        if self.thinking_level not in {
            "minimal", "low", "medium", "high"
        }:
            raise GeminiProviderError(
                "Invalid GEMINI_THINKING_LEVEL."
            )

        if self.thinking_budget >= self.max_tokens:
            raise GeminiProviderError(
                "Thinking budget must leave room for the answer."
            )

        if not self.model_id.startswith(
            ("gemini-2.5-flash", "gemini-3.")
        ):
            raise GeminiProviderError(
                "Configure a supported Gemini 2.5 Flash "
                "or Gemini 3 model."
            )

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        if not system_prompt.strip() or not user_prompt.strip():
            raise GeminiProviderError(
                "System and user prompts cannot be empty."
            )

        privacy = PrivacySession()

        try:
            system, user = privacy.protect_many(
                system_prompt.strip(),
                user_prompt.strip(),
            )
        except AIPrivacyError:
            raise GeminiProviderError(
                "AI privacy checks rejected the input."
            ) from None

        system += (
            "\n\nPrivacy handling:\n"
            "- Copy supplied __PF_ privacy placeholders exactly.\n"
            "- Never invent, decode, or expand privacy placeholders.\n"
            "- [SECRET_REMOVED] is unavailable; never reconstruct it.\n"
        )

        try:
            privacy.validate_outbound(system, user)
        except AIPrivacyError:
            raise GeminiProviderError(
                "AI privacy checks rejected the outbound input."
            ) from None

        thinking = (
            {"thinkingBudget": self.thinking_budget}
            if self.model_id.startswith("gemini-2.5-")
            else {"thinkingLevel": self.thinking_level}
        )

        data = await self.client.request(
            self.model_id,
            "generateContent",
            {
                "systemInstruction": {
                    "parts": [{"text": system}],
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user}],
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": self.max_tokens,
                    "thinkingConfig": thinking,
                },
            },
        )

        try:
            candidate = data["candidates"][0]

            if not isinstance(candidate, dict):
                raise ValueError

            if candidate.get("finishReason") != "STOP":
                raise GeminiProviderError(
                    "Gemini did not return a complete answer."
                )

            parts = candidate["content"]["parts"]

            if not isinstance(parts, list):
                raise ValueError

            answer = "\n".join(
                part["text"]
                for part in parts
                if (
                    isinstance(part, dict)
                    and not part.get("thought", False)
                    and isinstance(part.get("text"), str)
                )
            ).strip()

        except (KeyError, IndexError, TypeError, ValueError):
            raise GeminiProviderError(
                "Gemini returned no valid answer."
            ) from None

        if not answer:
            raise GeminiProviderError(
                "Gemini returned an empty answer."
            )

        try:
            return privacy.restore(answer)
        except AIPrivacyError:
            raise GeminiProviderError(
                "AI privacy checks rejected the response."
            ) from None


class GeminiEmbeddingProvider:
    def __init__(self) -> None:
        self.client = GeminiClient()
        self.model_id = "gemini-embedding-2"

        self.dimensions = integer_setting(
            "GEMINI_EMBEDDING_DIMENSIONS", 768, 768, 3072
        )

        if self.dimensions not in {768, 1536, 3072}:
            raise GeminiProviderError(
                "Gemini embedding dimensions must be "
                "768, 1536 or 3072."
            )

        self.model = (
            f"gemini:{self.model_id}:{self.dimensions}"
            f":search-v1:{EMBEDDING_PRIVACY_VERSION}"
        )

    def validate_vector(self, item: Any) -> list[float]:
        values = (
            item.get("values")
            if isinstance(item, dict)
            else None
        )

        if (
            not isinstance(values, list)
            or len(values) != self.dimensions
        ):
            raise GeminiProviderError(
                "Gemini returned an invalid embedding dimension."
            )

        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in values
        ):
            raise GeminiProviderError(
                "Gemini returned invalid embedding values."
            )

        vector = [float(value) for value in values]
        norm = math.hypot(*vector)

        if not math.isfinite(norm) or norm == 0:
            raise GeminiProviderError(
                "Gemini returned an invalid embedding norm."
            )

        return [value / norm for value in vector]

    async def _embed(
        self,
        texts: list[str],
        *,
        query: bool,
    ) -> list[list[float]]:
        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise GeminiProviderError(
                "Embedding inputs cannot be empty."
            )

        try:
            safe = [
                embedding_text(text.strip())
                for text in texts
            ]
        except AIPrivacyError:
            raise GeminiProviderError(
                "AI privacy checks rejected the embedding input."
            ) from None

        formatted = [
            (
                f"task: search result | query: {text}"
                if query
                else f"title: none | text: {text}"
            )
            for text in safe
        ]

        result: list[list[float]] = []

        for start in range(0, len(formatted), 16):
            batch = formatted[start:start + 16]

            data = await self.client.request(
                self.model_id,
                "batchEmbedContents",
                {
                    "requests": [
                        {
                            "model": f"models/{self.model_id}",
                            "content": {
                                "parts": [{"text": text}],
                            },
                            "embedContentConfig": {
                                "outputDimensionality": self.dimensions,
                            },
                        }
                        for text in batch
                    ]
                },
            )

            embeddings = data.get("embeddings")

            if (
                not isinstance(embeddings, list)
                or len(embeddings) != len(batch)
            ):
                raise GeminiProviderError(
                    "Gemini returned the wrong embedding count."
                )

            result.extend(
                self.validate_vector(item)
                for item in embeddings
            )

        return result

    async def embed_batch(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return await self._embed(texts, query=False)

    async def embed(self, text: str) -> list[float]:
        return (await self._embed([text], query=True))[0]