from typing import Any 

WEIGHTS = {
    "is_resolvable": 25,
    "has_mx": 30,
    "has_tls": 20,
    "homoglyph": 15, 
    "keyword": 20,
    "omission_or_transposition": 10,
    "tld_swap": 15, 
    "newly_registered": 25,
}

class BrandScoringService:
    @staticmethod 
    def evaluate(candidate: dict[str, Any], signals: dict[str, Any]) -> tuple[int, str, dict[str, Any]]:
        score = 0
        reasons: list[str] = [] 

        if signals.get("is_resolvable"):
            score += WEIGHTS["is_resolvable"]
            reasons.append(f"Domain resolves to active IP(s): {', '.join(signals['ip_addresses'][:2])}")

        if signals.get("has_mx"):
            score += WEIGHTS["has_mx"]
            reasons.append("Configured with MX records (capable of sending/receiving email)")

        if signals.get("has_tls"):
            score += WEIGHTS["has_tls"]
            reasons.append("HTTPS/TLS enabled on port 443")

        if signals.get("is_newly_registered"):
            score += WEIGHTS["newly_registered"]
            reasons.append(f"Smoking Gun: Domain is newly registered ({signals.get('days_old')} days old)")

        mutation_type = candidate.get("mutation_type", "")
        if mutation_type == "homoglyph":
            score += WEIGHTS["homoglyph"]
            reasons.append(f"Visual deception: {candidate.get('mutation_detail')}")
        elif "keyword" in mutation_type:
            score += WEIGHTS["keyword"]
            reasons.append(f"Contains sensitive phishing keyword: {candidate.get('mutation_detail')}")
        elif mutation_type == "tld_swap":
            score += WEIGHTS["tld_swap"]
            reasons.append(f"TLD Impersonation: {candidate.get('mutation_detail')}")
        else:
            score += WEIGHTS["omission_or_transposition"]
            reasons.append(f"Lexical variation: {candidate.get('mutation_detail')}")

        final_score = min(score, 100)

        if final_score >= 75:
            risk_level = "critical" if signals.get("has_mx") and signals.get("has_tls") else "high"
        elif final_score >= 50:
            risk_level = "medium"
        else:
            risk_level = "low"

        evidence = {
            "mutation": candidate, 
            "signals": signals, 
            "reasons": reasons,
            "weights_applied": {
                "base_mutation": mutation_type,
                "resolvable": signals.get("is_resolvable", False),
                "mx_enabled": signals.get("has_mx", False),
                "tls_enabled": signals.get("has_tls", False),
                "newly_registered": signals.get("is_newly_registered", False),
            },
        }

        return final_score, risk_level, evidence 