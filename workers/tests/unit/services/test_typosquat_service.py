from app.services.typosquat_service import TyposquatService


def test_generate_candidates_returns_results():
    candidates = TyposquatService.generate_candidates("hackerone.com")

    assert len(candidates) > 0


def test_generate_candidates_does_not_include_original_domain():
    candidates = TyposquatService.generate_candidates("hackerone.com")

    domains = [candidate["candidate_domain"] for candidate in candidates]

    assert "hackerone.com" not in domains


def test_generate_candidates_have_expected_fields():
    candidates = TyposquatService.generate_candidates("hackerone.com")

    candidate = candidates[0]

    assert "candidate_domain" in candidate
    assert "normalized_domain" in candidate
    assert "mutation_type" in candidate
    assert "mutation_detail" in candidate


def test_generate_candidates_include_character_omission():
    candidates = TyposquatService.generate_candidates("hackerone.com")

    mutation_types = [candidate["mutation_type"] for candidate in candidates]

    assert "omission" in mutation_types


def test_generate_candidates_are_unique():
    candidates = TyposquatService.generate_candidates("hackerone.com")

    domains = [candidate["candidate_domain"] for candidate in candidates]

    assert len(domains) == len(set(domains))