import tldextract
from typing import Any 

HOMOGLYPHS: dict[str, list[str]] = {
    "a": ["4", "@", "q", "c", "o"],
    "b": ["8", "6", "d", "p", "q"],
    "c": ["e", "o", "k"],
    "d": ["b", "p", "q", "cl"],
    "e": ["3", "c", "a", "o"],
    "f": ["t"],
    "g": ["q", "9", "6"],
    "h": ["b", "n"],
    "i": ["1", "l", "!", "j", "y"],
    "j": ["i", "y"],
    "k": ["x", "h"],
    "l": ["1", "i", "|", "I"],
    "m": ["rn", "n", "nn"],
    "n": ["m", "h", "r"],
    "o": ["0", "c", "q", "p", "d"],
    "p": ["q", "o", "b"],
    "q": ["g", "p", "9"],
    "r": ["n", "t"],
    "s": ["5", "$", "z", "c"],
    "t": ["7", "f", "l"],
    "u": ["v", "y", "w"],
    "v": ["u", "w", "y"],
    "w": ["vv", "v", "u"],
    "x": ["k", "y"],
    "y": ["j", "i", "v", "u"],
    "z": ["2", "s"],
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
    "sso",
    "mfa",
    "2fa", 
    "okta",
    "reset",
    "password",
    "enrollment",
    "service",
    "helpdesk",
    "security",
    "it",
    "mail",
    "webmail",
    "cloud",
    "app",
    "dev",
    "test",
    "stage",
    "api",
    "dashboard",
    "status",
    "vpn",
    "gateway",
    "connect",
    "network",
    "update",
    "billing",
    "payments",
    "invoice",
    "pay",
    "checkout",
    "alert",
    "checkout",
    "alert",
    "notice",
    "docs"
]

SUSPICIOUS_TLDS: list[str] = [
    "co", "net", "io", "xyz",
    "online", "ai", "shop", "tech", "info",
    "net", "org", "app", "dev", "cloud", "network",
    "space", "online", "biz", "name", "pro", "cc",
    "tv", "ws", "me", "pw", "top", "club", "site",
    "vip", "win", "bid", "review", "download", "zip",
    "click", "link", "website", "store", "cam", "icu"]

class TyposquatService:
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

        for tld in SUSPICIOUS_TLDS:
            if tld != suffix:
                _add(f"{name}.{tld}", "tld_swap", f"Swapped original TLD for '.{tld}'")

        return list(candidates.values())