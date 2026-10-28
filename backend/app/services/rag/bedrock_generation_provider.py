import asyncio
import os
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.services.ai_privacy import AIPrivacyError, PrivacySession
from app.services.rag.generation_provider import (
    GenerationProviderError,
)


class BedrockGenerationProviderError(GenerationProviderError):
    pass


class BedrockGenerationProvider:
    def __init__(self) -> None:
        self.region = os.getenv(
            "BEDROCK_GENERATION_REGION",
            os.getenv("BEDROCK_REGION", ""),
        ).strip()

        self.model_id = os.getenv(
            "BEDROCK_GENERATION_MODEL_ID",
            "",
        ).strip()

        max_tokens_value = os.getenv(
            "BEDROCK_GENERATION_MAX_TOKENS",
            "800",
        )

        temperature_value = os.getenv(
            "BEDROCK_GENERATION_TEMPERATURE",
            "0.1",
        )

        if not self.region:
            raise BedrockGenerationProviderError(
                "BEDROCK_GENERATION_REGION is not configured."
            )

        if not self.model_id:
            raise BedrockGenerationProviderError(
                "BEDROCK_GENERATION_MODEL_ID is not configured."
            )

        try:
            self.max_tokens = int(max_tokens_value)

        except ValueError as exc:
            raise BedrockGenerationProviderError(
                "BEDROCK_GENERATION_MAX_TOKENS must be an integer."
            ) from exc

        if not 1 <= self.max_tokens <= 8192:
            raise BedrockGenerationProviderError(
                "BEDROCK_GENERATION_MAX_TOKENS must be "
                "between 1 and 8192."
            )

        try:
            self.temperature = float(temperature_value)

        except ValueError as exc:
            raise BedrockGenerationProviderError(
                "BEDROCK_GENERATION_TEMPERATURE must be numeric."
            ) from exc

        if not 0.0 <= self.temperature <= 1.0:
            raise BedrockGenerationProviderError(
                "BEDROCK_GENERATION_TEMPERATURE must be "
                "between 0 and 1."
            )

        self.model = f"bedrock:{self.model_id}"

        try:
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
            )

        except BotoCoreError as exc:
            raise BedrockGenerationProviderError(
                "Amazon Bedrock generation could not be configured."
            ) from exc


    def generate_sync(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
    ) -> str:
        privacy = PrivacySession()

        try:
            safe_system_prompt = privacy.protect(system_prompt)
            safe_user_prompt = privacy.protect(user_prompt)

        except AIPrivacyError:
            raise BedrockGenerationProviderError(
                "AI privacy checks rejected the input."
            ) from None

        safe_system_prompt += (
            "\n\nPrivacy handling:\n"
            "- Copy supplied __PF_ privacy placeholders exactly "
            "when referring to their values.\n"
            "- Never invent, decode, or expand privacy placeholders.\n"
            "- [SECRET_REMOVED] indicates unavailable information; "
            "never reconstruct it.\n"
        )
        try:
            response: dict[str, Any] = self.client.converse(
                modelId=self.model_id,
                system=[
                    {
                        "text": safe_system_prompt,
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": safe_user_prompt,
                            }
                        ],
                    }
                ],
                inferenceConfig={
                    "maxTokens": self.max_tokens,
                    "temperature": self.temperature,
                },
            )

        except (BotoCoreError, ClientError):
            raise BedrockGenerationProviderError(
                "Amazon Bedrock rejected the generation request."
            ) from None

        try:
            content = response["output"]["message"]["content"]

        except (KeyError, TypeError) as exc:
            raise BedrockGenerationProviderError(
                "Amazon Bedrock returned an invalid generation response."
            ) from exc

        if not isinstance(content, list):
            raise BedrockGenerationProviderError(
                "Amazon Bedrock returned invalid answer content."
            )

        text_parts = [
            block["text"].strip()
            for block in content
            if (
                isinstance(block, dict)
                and isinstance(block.get("text"), str)
                and block["text"].strip()
            )
        ]

        answer = "\n".join(text_parts).strip()

        if not answer:
            raise BedrockGenerationProviderError(
                "Amazon Bedrock returned an empty answer."
            )

        try:
            return privacy.restore(answer)

        except AIPrivacyError:
            raise BedrockGenerationProviderError(
                "AI privacy checks rejected the response."
            ) from None


    async def generate(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
    ) -> str:
        normalized_system_prompt = system_prompt.strip()
        normalized_user_prompt = user_prompt.strip()

        if not normalized_system_prompt:
            raise BedrockGenerationProviderError(
                "The system prompt cannot be empty."
            )

        if not normalized_user_prompt:
            raise BedrockGenerationProviderError(
                "The user prompt cannot be empty."
            )

        return await asyncio.to_thread(
            self.generate_sync,
            system_prompt=normalized_system_prompt,
            user_prompt=normalized_user_prompt,
        )