import json

import pytest

from app.services.ai_privacy import (
    AIPrivacyError,
    PrivacySession,
    embedding_text,
)


def test_identifiers_are_masked_and_security_details_preserved():
    session = PrivacySession()

    protected = session.protect(
        "Company: Acme\n"
        "Acme admin@example.com 203.0.113.4 2001:db8::1 "
        "CVE-2025-12345 nginx 1.24.0"
    )

    for value in (
        "Acme",
        "admin@example.com",
        "203.0.113.4",
        "2001:db8::1",
    ):
        assert value not in protected
        assert value in session.restore(protected)

    assert "CVE-2025-12345" in protected
    assert "nginx 1.24.0" in protected


def test_credentials_and_url_secrets_are_not_restored():
    session = PrivacySession()

    protected = session.protect(
        'password="supersecret" '
        "https://user:pass@example.com/path?key=secret#private"
    )
    restored = session.restore(protected)

    for value in (
        "supersecret",
        "user:pass",
        "?key=",
        "#private",
    ):
        assert value not in protected
        assert value not in restored

    assert "https://example.com/path" in restored


def test_json_restoration_escapes_original_values():
    session = PrivacySession()
    original = 'Acme "Limited"\\Company'
    token = session.token("NAME", original)

    restored = session.restore(
        json.dumps({"answer": token})
    )

    assert json.loads(restored)["answer"] == original


def test_mapping_is_request_specific():
    first = PrivacySession()
    token = first.protect("api.example.com")

    with pytest.raises(AIPrivacyError):
        PrivacySession().restore(token)


def test_embedding_normalisation_is_stable():
    assert embedding_text(
        "api.example.com 203.0.113.4"
    ) == embedding_text(
        "other.test.net 198.51.100.1"
    )


def test_reserved_markers_and_oversized_inputs_fail_closed():
    with pytest.raises(AIPrivacyError):
        PrivacySession().protect("__PF_forged_0__")

    with pytest.raises(AIPrivacyError):
        PrivacySession().protect("x" * 120_001)


@pytest.mark.parametrize(
    "text",
    [
        "Authorization: Bearer private-credential",
        "Cookie: session=private-credential",
        (
            "-----BEGIN PRIVATE KEY-----\n"
            "private-credential\n"
            "-----END PRIVATE KEY-----"
        ),
        'api_key="private-credential"',
    ],
)
def test_recognised_secrets_are_removed(text):
    session = PrivacySession()
    protected = session.protect(text)

    assert "private-credential" not in protected
    assert "private-credential" not in session.restore(protected)


@pytest.mark.parametrize(
    "header",
    [
        "Cookie: session=private-credential",
        "Authorization: Bearer private-credential",
        "Set-Cookie: session=private-credential; HttpOnly",
    ],
)
def test_json_encoded_headers_are_removed(header):
    session = PrivacySession()

    raw = "Retrieved evidence:\n" + json.dumps(
        {
            "content": (
                header + "\nInspect nginx 1.24.0"
            ),
        }
    )

    protected = session.protect(raw)

    assert "private-credential" not in protected
    assert "private-credential" not in session.restore(protected)
    assert "nginx 1.24.0" in protected


@pytest.mark.parametrize(
    "key",
    ["cookie", "authorization", "session", "token"],
)
def test_json_secret_fields_are_removed(key):
    session = PrivacySession()

    protected = session.protect(
        json.dumps({key: "private-credential"})
    )

    assert "private-credential" not in protected
    assert "private-credential" not in session.restore(protected)