# auth.py — backend/tests/unit/test_auth.py
# _jwks_cache is module-level state, so tests clear it before/after
# each test to avoid leaking cached keys across tests.

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError

from app.api.middleware import auth as auth_module


@pytest.fixture(autouse=True)
def clear_jwks_cache():
    auth_module._jwks_cache.clear()
    yield
    auth_module._jwks_cache.clear()


def _credentials(token="fake.jwt.token"):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_to_rsa_key_extracts_expected_fields():
    jwk = {
        "kty": "RSA",
        "kid": "abc123",
        "use": "sig",
        "n": "modulus",
        "e": "AQAB",
        "alg": "RS256",  # should be dropped
    }

    result = auth_module._to_rsa_key(jwk)

    assert result == {
        "kty": "RSA",
        "kid": "abc123",
        "use": "sig",
        "n": "modulus",
        "e": "AQAB",
    }


@pytest.mark.asyncio
async def test_get_jwks_fetches_and_caches():
    mock_response = MagicMock()
    mock_response.json.return_value = {"keys": [{"kid": "key-1"}]}
    mock_response.raise_for_status = MagicMock()

    with patch.object(httpx.AsyncClient, "get", new=AsyncMock(return_value=mock_response)) as mock_get:
        first = await auth_module._get_jwks()
        second = await auth_module._get_jwks()

    assert first == [{"kid": "key-1"}]
    assert second == [{"kid": "key-1"}]
    # second call served from cache, no second HTTP call
    mock_get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_current_user_success():
    fake_keys = [{"kty": "RSA", "kid": "k1", "use": "sig", "n": "n", "e": "e"}]
    decoded_payload = {"sub": "user-1", "email": "user@example.com"}

    with patch.object(auth_module, "_get_jwks", new=AsyncMock(return_value=fake_keys)), \
            patch.object(auth_module.jwt, "decode", return_value=decoded_payload) as mock_decode:
        result = await auth_module.get_current_user(_credentials())

    assert result == decoded_payload
    mock_decode.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_user_invalid_token_raises_401():
    fake_keys = [{"kty": "RSA", "kid": "k1", "use": "sig", "n": "n", "e": "e"}]

    with patch.object(auth_module, "_get_jwks", new=AsyncMock(return_value=fake_keys)), \
            patch.object(auth_module.jwt, "decode", side_effect=JWTError("bad signature")):
        with pytest.raises(HTTPException) as exc_info:
            await auth_module.get_current_user(_credentials())

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_jwks_unreachable_raises_503():
    with patch.object(auth_module, "_get_jwks", new=AsyncMock(side_effect=httpx.RequestError("timeout"))):
        with pytest.raises(HTTPException) as exc_info:
            await auth_module.get_current_user(_credentials())

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_get_current_user_unexpected_error_raises_500():
    with patch.object(auth_module, "_get_jwks", new=AsyncMock(side_effect=ValueError("boom"))):
        with pytest.raises(HTTPException) as exc_info:
            await auth_module.get_current_user(_credentials())

    assert exc_info.value.status_code == 500