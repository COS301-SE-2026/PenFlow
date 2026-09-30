from app.services.brand_scoring_service import BrandScoringService

#testing low rated scoring
def test_low_risk_lexical_var():
    candidate = {
        "mutation_type": "omission",
        "mutation_detail": "removed one char",
    }
    signals = {
        "is_resolvable": False,
        "has_mx": False,
        "has_tls": False,
        "is_newly_registered": False,
    }

    score, risk, evidence = (
        BrandScoringService.evaluate(candidate, signals))

    assert score == 10
    assert risk == "low"
    assert "Lexical variation" in evidence["reasons"][0]

#testing medium rated scoring
def test_medium_risk_homoglyph():
    candidate = {
        "mutation_type": "homoglyph",
        "mutation_detail": "replaced o and 0",
    }
    signals = {
        "is_resolvable": True,
        "ip_addresses": ["1.2.3.4"],
        "has_mx": False,
        "has_tls": False,
        "is_newly_registered": False,
    }

    score, risk, evidence = (
        BrandScoringService.evaluate(candidate, signals))

    assert score == 40
    assert risk == "low"
    assert evidence["weights_applied"]["resolvable"] is True
    assert any("Visual deception" in reason for reason in evidence["reasons"])

#testing medium rated scoring
def test_medium_risk_keyword():
    candidate = {
        "mutation_type": "keyword_prefix",
        "mutation_detail": "login",
    }
    signals = {
        "is_resolvable": True,
        "ip_addresses": ["1.2.3.4"],
        "has_mx": False,
        "has_tls": False,
        "is_newly_registered": True,
        "days_old": 3,
    }

    score, risk, evidence = (
        BrandScoringService.evaluate(candidate, signals))

    assert score == 70
    assert risk == "medium"
    assert any("newly registered" in reason for reason in evidence["reasons"])
    assert any("phishing keyword" in reason for reason in evidence["reasons"])

#testing high rated scoring
def test_high_risk():
    candidate = {
        "mutation_type": "tld_swap",
        "mutation_detail": ".com to .net",
    }
    signals = {
        "is_resolvable": True,
        "ip_addresses": ["1.2.3.4"],
        "has_mx": False,
        "has_tls": True,
        "is_newly_registered": True,
        "days_old": 2,
    }

    score, risk, evidence = BrandScoringService.evaluate(candidate, signals)

    assert score == 85
    assert risk == "high"
    assert any("TLD Impersonation" in reason for reason in evidence["reasons"])

#testing critical rated scoring
def test_critical_risk():
    candidate = {
        "mutation_type": "keyword_suffix",
        "mutation_detail": "secure",
    }
    signals = {
        "is_resolvable": True,
        "ip_addresses": ["1.2.3.4", "5.6.7.8", "9.10.11.12"],
        "has_mx": True,
        "has_tls": True,
        "is_newly_registered": True,
        "days_old": 1,
    }

    score, risk, evidence = (
        BrandScoringService.evaluate(candidate, signals))

    assert score == 100

    assert risk == "critical"
    assert evidence["weights_applied"]["mx_enabled"] is True
    assert evidence["weights_applied"]["tls_enabled"] is True
    assert evidence["weights_applied"]["newly_registered"] is True
    assert any("MX records" in reason for reason in evidence["reasons"])
    assert any("HTTPS/TLS" in reason for reason in evidence["reasons"])