import json
import re
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.services.ai_privacy import (
    EMBEDDING_PRIVACY_VERSION,
    AIPrivacyError,
    PrivacySession,
)
from app.services.rag import gemini_provider
from app.services.rag.bedrock_embedding_provider import (
    BedrockEmbeddingProvider,
)
from app.services.rag.bedrock_generation_provider import (
    BedrockGenerationProvider,
    BedrockGenerationProviderError,
)
from app.services.rag.embedding_service import EmbeddingService


@pytest.mark.asyncio
@pytest.mark.parametrize("label_in_system", [False, True])
async def test_gemini_sends_no_known_name_from_either_prompt(
    monkeypatch,
    label_in_system,
):
    monkeypatch.setenv(
        "GEMINI_API_KEY",
        "synthetic-test-key",
    )

    real_client = httpx.AsyncClient
    sent = []

    def handler(request):
        body = json.loads(request.content)
        sent.append(body)

        assert "Acme Example" not in json.dumps(body)

        text = body["contents"][0]["parts"][0]["text"]

        token = re.search(
            r"__PF_[A-Za-z0-9_]+__",
            text,
        ).group()

        return httpx.Response(
            200,
            json={
                "candidates": [{
                    "finishReason": "STOP",
                    "content": {
                        "parts": [{"text": token}],
                    },
                }],
            },
        )

    monkeypatch.setattr(
        gemini_provider.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(handler),
            **kwargs,
        ),
    )

    system = "Company: Acme Example"
    user = "Explain Acme Example"

    if not label_in_system:
        system, user = user, system

    answer = await (
        gemini_provider.GeminiGenerationProvider().generate(
            system_prompt=system,
            user_prompt=user,
        )
    )

    assert answer == "Acme Example"
    assert len(sent) == 1


@pytest.mark.parametrize("label_in_system", [False, True])
def test_bedrock_sends_no_known_name_from_either_prompt(
    label_in_system,
):
    provider = BedrockGenerationProvider.__new__(
        BedrockGenerationProvider
    )

    provider.model_id = "synthetic-model"
    provider.max_tokens = 800
    provider.temperature = 0.1
    provider.client = Mock()

    provider.client.converse.return_value = {
        "output": {
            "message": {
                "content": [{"text": "Audit response"}],
            },
        },
    }

    system = "Company: Acme Example"
    user = "Explain Acme Example"

    if not label_in_system:
        system, user = user, system

    provider.generate_sync(
        system_prompt=system,
        user_prompt=user,
    )

    assert "Acme Example" not in json.dumps(
        provider.client.converse.call_args.kwargs
    )


def test_all_embedding_provider_ids_use_current_privacy_version(
    monkeypatch,
):
    import app.services.rag.bedrock_embedding_provider as module

    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("BEDROCK_REGION", "eu-north-1")
    monkeypatch.setattr(module.boto3, "client", Mock())

    providers = [
        gemini_provider.GeminiEmbeddingProvider(),
        EmbeddingService(),
        BedrockEmbeddingProvider(),
    ]

    for provider in providers:
        assert provider.model.endswith(
            ":" + EMBEDDING_PRIVACY_VERSION
        )

        assert not provider.model.endswith(":privacy-v1")


@pytest.mark.asyncio
async def test_gemini_does_not_send_when_final_validation_fails(
    monkeypatch,
):
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-test-key")

    provider = gemini_provider.GeminiGenerationProvider()
    request = AsyncMock()

    monkeypatch.setattr(
        provider.client,
        "request",
        request,
    )

    original = PrivacySession.validate_outbound
    calls = 0

    def validate(self, *parts):
        nonlocal calls
        calls += 1

        if calls == 2:
            raise AIPrivacyError(
                "Synthetic final-check failure"
            )

        return original(self, *parts)

    monkeypatch.setattr(
        PrivacySession,
        "validate_outbound",
        validate,
    )

    with pytest.raises(
        gemini_provider.GeminiProviderError,
        match="outbound",
    ):
        await provider.generate(
            system_prompt="Explain",
            user_prompt="private.example",
        )

    request.assert_not_awaited()


def test_bedrock_does_not_send_when_final_validation_fails(
    monkeypatch,
):
    provider = BedrockGenerationProvider.__new__(
        BedrockGenerationProvider
    )

    provider.client = Mock()
    original = PrivacySession.validate_outbound
    calls = 0

    def validate(self, *parts):
        nonlocal calls
        calls += 1

        if calls == 2:
            raise AIPrivacyError(
                "Synthetic final-check failure"
            )

        return original(self, *parts)

    monkeypatch.setattr(
        PrivacySession,
        "validate_outbound",
        validate,
    )

    with pytest.raises(
        BedrockGenerationProviderError,
        match="outbound",
    ):
        provider.generate_sync(
            system_prompt="Explain",
            user_prompt="private.example",
        )

    provider.client.converse.assert_not_called()