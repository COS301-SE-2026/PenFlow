import json

import pytest

from app.services.ai_privacy import (
    AIPrivacyError,
    PrivacySession,
    embedding_text,
)


@pytest.mark.parametrize(
    "field",
    ["title", "description", "question", "previous_user_question"],
)
@pytest.mark.parametrize(
    "separator",
    ["\n", "\r", "\t", r"\n"],
)
@pytest.mark.parametrize(
    "identifier",
    [
        "203.0.113.4",
        "2001:0db8:0000:0000:0000:0000:0000:0001",
        "::ffff:203.0.113.4",
    ],
)
@pytest.mark.parametrize("embedding", [False, True])
def test_identifiers_after_json_separators(
    field,
    separator,
    identifier,
    embedding,
):
    raw = json.dumps({
        field: "Evidence:" + separator + identifier,
    })

    session = PrivacySession(embedding=embedding)
    protected = session.protect(raw)

    assert identifier not in protected
    assert identifier not in json.loads(protected)[field]

    if not embedding:
        assert (
            json.loads(session.restore(protected))
            == json.loads(raw)
        )


@pytest.mark.parametrize(
    "identifier",
    [
        "bücher.example",
        "example.рф",
        "xn--bcher-kva.example",
        '"a b"@private.example',
        "admin+audit@private.example",
        "user@[203.0.113.4]",
        "fe80::1%eth0",
    ],
)
@pytest.mark.parametrize("serialized", [False, True])
def test_supported_address_forms_are_masked(
    identifier,
    serialized,
):
    value = "Recorded asset: " + identifier

    raw = (
        json.dumps({"description": value})
        if serialized
        else value
    )

    session = PrivacySession()
    protected = session.protect(raw)

    assert identifier not in protected

    restored = session.restore(protected)

    if serialized:
        assert json.loads(restored) == json.loads(raw)
    else:
        assert restored == raw


@pytest.mark.parametrize(
    "header",
    [
        "Authorization: Bearer demo-secret",
        "Proxy-Authorization: Basic ZGVtby11c2VyOmRlbW8tc2VjcmV0",
        "Cookie: sid=demo-secret; tracking=demo-other",
        "Set-Cookie: sid=demo-secret; HttpOnly",
    ],
)
@pytest.mark.parametrize("serialized", [False, True])
def test_complete_inline_headers_are_removed(
    header,
    serialized,
):
    raw = (
        "Recorded header: "
        + header
        + "\nInspect nginx 1.24.0"
    )

    if serialized:
        raw = json.dumps({"description": raw})

    session = PrivacySession()
    protected = session.protect(raw)
    restored = session.restore(protected)

    for secret in (
        "demo-secret",
        "demo-other",
        "ZGVtby11c2VyOmRlbW8tc2VjcmV0",
    ):
        assert secret not in protected
        assert secret not in restored

        assert all(
            secret not in original
            for original in session.mapping.values()
        )

    assert "nginx 1.24.0" in protected

    if serialized:
        json.loads(protected)
        json.loads(restored)


@pytest.mark.parametrize(
    "secret",
    [
        "AIza" + "A" * 35,
        "github_pat_" + "A" * 80,
    ],
)
@pytest.mark.parametrize("serialized", [False, True])
def test_additional_secret_signatures_are_never_restored(
    secret,
    serialized,
):
    raw = (
        json.dumps({"description": "Credential " + secret})
        if serialized
        else secret
    )

    session = PrivacySession()
    protected = session.protect(raw)

    assert secret not in protected
    assert secret not in session.restore(protected)

    assert all(
        secret not in value
        for value in session.mapping.values()
    )


@pytest.mark.parametrize(
    "name",
    ['Acme "Limited"', "Acme \\ Finance"],
)
def test_known_escaped_names_are_removed_from_sibling_fields(name):
    raw = json.dumps({
        "description": "Finding for " + name,
        "full_name": name,
    })

    session = PrivacySession()
    protected = session.protect(raw)
    fields = json.loads(protected)

    assert name not in fields["description"]
    assert name not in fields["full_name"]

    assert (
        json.loads(session.restore(protected))
        == json.loads(raw)
    )


def test_nested_json_strings_are_redacted_without_corruption():
    raw = json.dumps({
        "evidence": json.dumps({
            "description": "Evidence:\n203.0.113.4",
        }),
    })

    session = PrivacySession()
    protected = session.protect(raw)

    inner = json.loads(
        json.loads(protected)["evidence"]
    )

    assert "203.0.113.4" not in inner["description"]

    restored = json.loads(session.restore(protected))

    assert (
        json.loads(restored["evidence"])["description"]
        == "Evidence:\n203.0.113.4"
    )


def test_sensitive_json_keys_are_scrubbed_even_when_escaped():
    raw = (
        r'{"pass\u0077ord":"demo-secret",'
        r'"nested":{"api_key":"demo-key"}}'
    )

    safe = PrivacySession().protect(raw)

    assert "demo-secret" not in safe
    assert "demo-key" not in safe
    json.loads(safe)


def test_identifier_dictionary_keys_restore_locally():
    raw = json.dumps({"private.example": "asset"})

    session = PrivacySession()
    safe = session.protect(raw)

    assert "private.example" not in safe
    assert json.loads(session.restore(safe)) == json.loads(raw)


def test_technical_context_and_finding_uuid_are_preserved():
    text = (
        "Port 443/tcp is open. CVE-2025-12345 affects nginx 1.24.0. "
        "TLS 1.3; CVSS 9.8. "
        "Finding ID: 22222222-2222-4222-8222-222222222222"
    )

    assert PrivacySession().protect(text) == text


def test_url_secrets_are_not_restored():
    session = PrivacySession()

    safe = session.protect(
        "https://user:pass@private.example/path"
        "?token=demo-secret#fragment"
    )

    restored = session.restore(safe)

    assert restored == "https://private.example/path"
    assert "demo-secret" not in restored


@pytest.mark.parametrize(
    "text",
    [
        '{"description":"203.0.113.4',
        "[x" * 513,
        "[" * 25 + '"203.0.113.4"' + "]" * 25,
        r'{"description":"\u005f\u005fPF_forged_0__"}',
    ],
)
def test_malformed_deep_or_reserved_input_fails_closed(text):
    with pytest.raises(AIPrivacyError) as caught:
        PrivacySession().protect(text)

    assert "203.0.113.4" not in str(caught.value)


def test_embedding_replacement_remains_stable():
    first = json.dumps({
        "content": "Host:\n203.0.113.4",
    })

    second = json.dumps({
        "content": "Host:\n198.51.100.2",
    })

    assert embedding_text(first) == embedding_text(second)