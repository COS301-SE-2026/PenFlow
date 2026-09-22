import tldextract
from typing import Any 

HOMOGLYPHS: dict[str, list[str]] = {
    "a": ["4", "@"],
    "e": ["3"],
    "i": ["1", "l", "!"],
    "l": ["1", "i"],
    "o": ["0"],
    "s": ["5", "$"],
    "t": ["7"],
}

SECURITY_KEYWORDS: list[str] = [
    "login",
    "secure",
    "portal",
    "auth",
    "verify",
    "support",
    "admin",
    "account",
]

class TyposqautService:
    @staticmethod
    def extract_domain_parts(domain: str) -> tuple[str, str]:
        """
        Splits domain into registered domain name and suffix
        """
        extracted = tldextract.extract(domain)
        return extracted.domain, extracted.suffix

    @classmethod 
    def generate_candidates(cls, domain: str) -> list[dict[str, Any]]:
        name, suffix = cls.extract_domain_parts(domain)
        candidates: dict[str, dict[str, Any]] = {}

        def _add(cand_domain: str, mutation_type: str, detail: str) -> None:
            if cand_domain != domain and cand_domain not in candidates:
                candidates[cand_domain] = {
                    "candidate_domain": cand_domain,
                    "normalized_domain": cand_domain.lower().strip(),
                    "mutation_type": mutation_type,
                    "mutation_detail": detail,
                }

        for i, char in enumerate(name):
            if char in HOMOGLYPHS:
                for sub in HOMOGLYPHS[char]:
                    mutated = name[:i] + sub + name[i + 1 :]
                    _add(f"{mutated}.{suffix}", "homoglyph", f"Replaced '{char}' with '{sub}'")

        for i in range(len(name)):
            mutated = name[:i] + name[i + 1 :]
            if len(mutated) >= 3:
                _add(f"{mutated}.{suffix}", "omission", f"Omitted character at index {i}")

        name_chars = list(name)
        for i in range(len(name_chars) - 1):
            swapped = name_chars.copy()
            swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
            _add(f"{''.join(swapped)}.{suffix}", "transposition", f"Swapped '{swapped[i+1]}' and '{swapped[i]}'")

        for kw in SECURITY_KEYWORDS:
            _add(f"{name}-{kw}.{suffix}", "keyword_suffix", f"Appended keyword '-{kw}'")
            _add(f"{kw}-{name}.{suffix}", "keyword_prefix", f"Prepend keyword '{kw}-'")
            _add(f"{name}{kw}.{suffix}", "keyword_affix", f"Concatenated keyword '{kw}'")

        return list(candidates.values())