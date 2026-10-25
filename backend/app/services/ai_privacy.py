import ipaddress
import json
import re
import secrets
from typing import Any
from urllib.parse import urlsplit, urlunsplit


class AIPrivacyError(ValueError):
    pass


SECRET_PATTERNS = (
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?"
        r"(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)",
        re.DOTALL,
    ),
    re.compile(
        r"(?im)^\s*"
        r"(?:authorization|proxy-authorization|cookie|set-cookie)"
        r"\s*:[^\r\n]*"
    ),
    re.compile(
        r"""(?ix)
        (
            ["']?
            (?:
                password|passwd|secret|client_secret|
                api[_-]?key|access[_-]?token|refresh[_-]?token|
                session[_-]?id|session|token|
                authorization|cookie|set[_-]cookie
            )
            ["']?\s*[:=]\s*
        )
        (?:
            "(?:\\.|[^"\\])*"
            |
            '(?:\\.|[^'\\])*'
            |
            [^\s,;}]+
        )
        """
    ),
    re.compile(
        r"\beyJ[A-Za-z0-9_-]+\."
        r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"
    ),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{16,}|"
        r"gh[pousr]_[A-Za-z0-9_]{20,})\b"
    ),
    re.compile(
        r"(?i)\b(?:Bearer|Basic)\s+[A-Za-z0-9+/_.=:-]+"
    ),
)

URL = re.compile(
    r"""(?i)\b[a-z][a-z0-9+.-]*://[^\s<>"'\\]+"""
)

EMAIL = re.compile(
    r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
)

HOST = re.compile(
    r"(?i)(?<![\w@-])"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z]{2,63}\b"
)

IP = re.compile(
    r"(?<![\w])"
    r"(?:[0-9a-fA-F]*:[0-9a-fA-F:.]+|"
    r"(?:\d{1,3}\.){3}\d{1,3})"
    r"(?![\w])"
)

LABEL = re.compile(
    r"(?im)^"
    r"(\s*(?:company|organisation|organization|client name|"
    r"primary contact|assigned pentester|service delivery)"
    r"\s*:\s*)"
    r"([^\r\n]+)"
)

JSON_NAME = re.compile(
    r'("(?:company(?:_name)?|organisation(?:_name)?|'
    r"organization(?:_name)?|client_name|full_name|"
    r"primary_contact|assigned_pentester_name|"
    r'service_delivery_name)"\s*:\s*)'
    r'("(?:\\.|[^"\\])*")',
    re.IGNORECASE,
)


JSON_STRING = re.compile(r'"(?:\\.|[^"\\])*"')


def remove_secrets(text: str) -> str:
    def scrub(value: str) -> str:
        for pattern in SECRET_PATTERNS:
            value = pattern.sub(
                lambda match: (
                    match.group(1) + '"[SECRET_REMOVED]"'
                    if match.lastindex
                    else "[SECRET_REMOVED]"
                ),
                value,
            )

        return value

    def scrub_json_string(match: re.Match[str]) -> str:
        try:
            decoded = json.loads(match.group())
        except json.JSONDecodeError:
            return match.group()

        return json.dumps(
            scrub(decoded),
            ensure_ascii=False,
        )

    return scrub(
        JSON_STRING.sub(scrub_json_string, text)
    )


class PrivacySession:

    def __init__(self, *, embedding: bool = False) -> None:
        self.embedding = embedding
        self.nonce = secrets.token_hex(12)
        self.mapping: dict[str, str] = {}
        self.tokens: dict[tuple[str, str], str] = {}

    def token(self, kind: str, value: str) -> str:
        if self.embedding:
            return f"[{kind}]"

        key = (kind, value)

        if key not in self.tokens:
            token = (
                f"__PF_{self.nonce}_{len(self.mapping)}__"
            )
            self.tokens[key] = token
            self.mapping[token] = value

        return self.tokens[key]

    def protect(self, text: str) -> str:
        if "__PF_" in text:
            raise AIPrivacyError(
                "Reserved privacy marker in AI input."
            )

        if len(text) > 120_000:
            raise AIPrivacyError(
                "AI input exceeds the privacy processing limit"
            )

        text = remove_secrets(text)

        names = {
            match.group(2).strip()
            for match in LABEL.finditer(text)
        }

        json_names = [
            json.loads(match.group(2))
            for match in JSON_NAME.finditer(text)
        ]

        names.update(json_names)

        text = JSON_NAME.sub(
            lambda match: (
                match.group(1)
                + json.dumps(
                    self.token(
                        "NAME",
                        json.loads(match.group(2)),
                    )
                )
            ),
            text,
        )

        for name in sorted(names, key=len, reverse=True):
            if name and name not in {
                "None",
                "Not provided",
                "[SECRET_REMOVED]",
            }:
                text = text.replace(
                    name,
                    self.token("NAME", name),
                )

        text = URL.sub(self._url, text)

        text = EMAIL.sub(
            lambda match: self.token(
                "EMAIL",
                match.group(),
            ),
            text,
        )

        text = IP.sub(self._ip, text)

        return HOST.sub(
            lambda match: self.token(
                "HOST",
                match.group(),
            ),
            text,
        )

    def _url(self, match: re.Match[str]) -> str:
        try:
            parts = urlsplit(match.group())
            host = parts.hostname

            if not host:
                return "[URL_REMOVED]"

            netloc = f"[{host}]" if ":" in host else host

            if parts.port is not None:
                netloc += f":{parts.port}"

            clean = urlunsplit(
                (
                    parts.scheme,
                    netloc,
                    parts.path,
                    "",
                    "",
                )
            )

            return self.token("URL", clean)

        except ValueError:
            return "[URL_REMOVED]"


    def _ip(self, match: re.Match[str]) -> str:
        try:
            ipaddress.ip_address(match.group())
        except ValueError:
            return match.group()

        return self.token("IP", match.group())

    def restore(self, answer: str) -> str:
        pattern = re.compile(r"__PF_[A-Za-z0-9_]+__")

        def replace(match: re.Match[str]) -> str:
            token = match.group()

            if token not in self.mapping:
                raise AIPrivacyError(
                    "AI response contains an unknown privacy marker."
                )

            return self.mapping[token]

        def walk(value: Any) -> Any:
            if isinstance(value, str):
                return pattern.sub(replace, value)

            if isinstance(value, list):
                return [walk(item) for item in value]

            if isinstance(value, dict):
                return {
                    key: walk(item)
                    for key, item in value.items()
                }

            return value

        candidate = answer.strip()

        if (
            candidate.startswith("```json\n")
            and candidate.endswith("```")
        ):
            candidate = candidate[8:-3].strip()

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return pattern.sub(replace, answer)

        return json.dumps(
            walk(payload),
            ensure_ascii=False,
        )

def embedding_text(text: str) -> str:
    return PrivacySession(embedding=True).protect(text)