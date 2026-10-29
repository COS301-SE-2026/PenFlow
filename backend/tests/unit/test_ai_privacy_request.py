import json

import pytest

from app.services.ai_privacy import AIPrivacyError, PrivacySession


@pytest.mark.parametrize("label_in_system", [False, True])
@pytest.mark.parametrize(
    "name",
    ["Acme Example", 'Acme "Limited"'],
)
def test_names_are_discovered_before_either_prompt_is_protected(
    label_in_system,
    name,
):
    labelled = json.dumps({"company_name": name})
    question = "Explain the findings for " + name

    parts = (
        (labelled, question)
        if label_in_system
        else (question, labelled)
    )

    session = PrivacySession()
    protected = session.protect_many(*parts)

    assert name not in " ".join(protected)

    labelled_index = 0 if label_in_system else 1
    question_index = 1 if label_in_system else 0

    assert name not in str(json.loads(protected[labelled_index]))

    assert (
        session.restore(protected[question_index])
        == question
    )


def test_names_remain_known_for_later_calls_within_the_session():
    session = PrivacySession()
    session.protect("Company: Acme Example")

    assert (
        "Acme Example"
        not in session.protect("Question about Acme Example")
    )


def test_exact_secret_repetitions_are_removed_and_never_restored():
    session = PrivacySession()

    protected = session.protect_many(
        "The recorded value is demo-secret",
        json.dumps({"password": "demo-secret"}),
    )

    for part in protected:
        assert "demo-secret" not in part
        assert "demo-secret" not in session.restore(part)

    assert all(
        "demo-secret" not in value
        for value in session.mapping.values()
    )


def test_embedded_cookie_values_are_removed_from_other_parts():
    protected = PrivacySession().protect_many(
        "Recorded values: cookie-secret and tracking-secret",
        "Header: Cookie: sid=cookie-secret; tracking=tracking-secret",
    )

    assert "cookie-secret" not in str(protected)
    assert "tracking-secret" not in str(protected)


@pytest.mark.parametrize("encoded", [False, True])
def test_outbound_check_rejects_known_identifier_in_plain_or_decoded_json(
    encoded,
):
    session = PrivacySession()
    session.protect("private.example")

    raw = (
        r'{"description":"private\u002eexample"}'
        if encoded
        else "private.example"
    )

    with pytest.raises(AIPrivacyError) as caught:
        session.validate_outbound(raw)

    assert "private.example" not in str(caught.value)


def test_outbound_check_rejects_raw_secret_json_values():
    with pytest.raises(AIPrivacyError):
        PrivacySession().validate_outbound(
            '{"password":"demo-secret"}'
        )


def test_outbound_guard_catches_a_broken_redactor(monkeypatch):
    session = PrivacySession()

    monkeypatch.setattr(
        session,
        "_host",
        lambda match: match.group(),
    )

    with pytest.raises(AIPrivacyError):
        session.protect("private.example")


def test_allowed_markers_do_not_trigger_short_name_false_positive():
    protected = PrivacySession().protect_many(
        "Company: e",
        "e",
    )

    assert protected[1].startswith("__PF_")


def test_unknown_outbound_marker_is_rejected():
    with pytest.raises(AIPrivacyError):
        PrivacySession().validate_outbound(
            "__PF_unknown_0__"
        )


def test_secret_matching_preserves_unrelated_technical_numbers():
    protected = PrivacySession().protect_many(
        "password=123",
        "CVE-2025-12345; port 443",
    )

    assert "123" not in protected[0]
    assert protected[1] == "CVE-2025-12345; port 443"


def test_request_discovery_is_not_shared_between_users():
    first = PrivacySession()
    first.protect("Company: Acme Example")

    second = PrivacySession()

    assert second.protect("Acme Example") == "Acme Example"