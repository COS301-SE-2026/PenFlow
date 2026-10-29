import ipaddress
import json
import re
import secrets
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit, urlunsplit


class AIPrivacyError(ValueError):
    pass


MAX_INPUT = 120_000
MAX_DEPTH = 16
MAX_FRAGMENTS = 512
MAX_KNOWN_VALUES = 2048
EMBEDDING_PRIVACY_VERSION = "privacy-v2"
REMOVED = "[SECRET_REMOVED]"

PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?"
    r"(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)",
    re.DOTALL,
)

HEADER = re.compile(
    r"(?im)(?<![\w-])(?:authorization|proxy-authorization|cookie|set-cookie)"
    r"\s*:[^\r\n]*"
)

AUTH_TOKEN = re.compile(
    r"(?i)\b(?:Bearer|Basic)\s+[A-Za-z0-9+/_.=:-]+"
)

SECRET_KEY = re.compile(
    r"(?:[a-z][a-z0-9]*[_-])*"
    r"(?:password|passwd|secret|client_secret|api[_-]?key|access[_-]?token|"
    r"refresh[_-]?token|session[_-]?id|session|token|authorization|"
    r"proxy[_-]?authorization|cookie|set[_-]?cookie)",
    re.IGNORECASE | re.VERBOSE,
)

SECRET_ASSIGNMENT = re.compile(
    r"(?ix)(?<![\w-])([\"']?" + SECRET_KEY.pattern + r"[\"']?\s*[:=]\s*)"
    r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s,;}]+)"
)

SECRET_SIGNATURES = (
    re.compile(
        r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"
    ),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,})\b"
    ),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b"),
)

URL = re.compile(
    r"(?i)\b[a-z][a-z0-9+.-]*://[^\s<>\"'\\]+"
)

LABEL_PART = r"[^\W_](?:[^\W_]|-){0,62}"
DOMAIN = rf"(?:{LABEL_PART}\.)+{LABEL_PART}"

EMAIL = re.compile(
    r"(?<![\w@])(?:\"(?:[^\"\\\r\n]|\\.)+\"|[\w.!#$%&'*+/=?^`{|}~-]+)"
    rf"@(?:{DOMAIN}|\[[0-9a-fA-F:.]+\])(?![\w-])"
)

HOST = re.compile(
    rf"(?<![\w@-]){DOMAIN}(?![\w-])"
)

IP = re.compile(
    r"(?<![\w])(?:[0-9a-fA-F]*:[0-9a-fA-F:.]+(?:%[\w.-]+)?|"
    r"(?:\d{1,3}\.){3}\d{1,3})(?![\w])"
)

NAME_KEYS = {
    "company",
    "company_name",
    "organisation",
    "organisation_name",
    "organization",
    "organization_name",
    "client_name",
    "full_name",
    "primary_contact",
    "assigned_pentester",
    "assigned_pentester_name",
    "service_delivery",
    "service_delivery_name",
}

LABEL = re.compile(
    r"(?im)^[ \t]*(company|organisation|organization|client name|"
    r"primary contact|assigned pentester|service delivery)[ \t]*:[ \t]*([^\r\n]+)"
)


def _key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _strip_secrets(text: str) -> str:
    text = PRIVATE_KEY.sub(REMOVED, text)
    text = HEADER.sub(REMOVED, text)
    text = AUTH_TOKEN.sub(REMOVED, text)

    for pattern in SECRET_SIGNATURES:
        text = pattern.sub(REMOVED, text)

    return SECRET_ASSIGNMENT.sub(
        lambda match: match.group(1) + REMOVED,
        text,
    )


def _transform(
    text: str,
    plain: Callable[[str], str],
    *,
    on_name: Callable[[str], None] | None = None,
    on_secret: Callable[[Any], None] | None = None,
    allow_markers: bool = False,
    depth: int = 0,
) -> str:
    if depth > MAX_DEPTH:
        raise AIPrivacyError(
            "AI input exceeds the privacy nesting limit."
        )

    if not allow_markers and "__PF_" in text:
        raise AIPrivacyError(
            "Reserved privacy marker in AI input."
        )

    def walk(value: Any, level: int = depth + 1) -> Any:
        if level > MAX_DEPTH:
            raise AIPrivacyError(
                "AI input exceeds the privacy nesting limit."
            )

        if isinstance(value, str):
            return _transform(
                value,
                plain,
                on_name=on_name,
                on_secret=on_secret,
                allow_markers=allow_markers,
                depth=level,
            )

        if isinstance(value, list):
            return [
                walk(item, level + 1)
                for item in value
            ]

        if isinstance(value, dict):
            result = {}

            for key, item in value.items():
                if SECRET_KEY.fullmatch(_key(key)):
                    if on_secret:
                        on_secret(item)

                    result[key] = REMOVED
                    continue

                if (
                    on_name
                    and _key(key) in NAME_KEYS
                    and isinstance(item, str)
                ):
                    on_name(_strip_secrets(item).strip())

                result[plain(key)] = walk(item, level + 1)

            return result

        return value

    stripped = text.strip()

    if stripped.startswith('"'):
        try:
            value = json.loads(stripped)
        except (ValueError, RecursionError):
            pass
        else:
            if isinstance(value, str):
                return json.dumps(
                    walk(value),
                    ensure_ascii=False,
                )

    decoder = json.JSONDecoder()
    pieces: list[str] = []
    last = 0
    index = 0
    fragments = 0

    while index < len(text):
        if text[index] not in "{[":
            index += 1
            continue

        start = index
        fragments += 1

        if fragments > MAX_FRAGMENTS:
            raise AIPrivacyError(
                "AI input exceeds the privacy fragment limit."
            )

        try:
            value, end = decoder.raw_decode(text, start)
        except RecursionError:
            raise AIPrivacyError(
                "AI input exceeds the privacy nesting limit."
            ) from None

        except ValueError:
            remainder = text[start + 1:].lstrip()

            if text[start] == "[" and "]" in remainder:
                candidate = remainder.split("]", 1)[0]

                try:
                    ipaddress.ip_address(candidate)
                except ValueError:
                    pass
                else:
                    index += 1
                    continue

            if remainder.startswith(('"', "{", "[")):
                raise AIPrivacyError(
                    "Malformed structured AI input."
                ) from None

            index += 1
            continue

        pieces.append(plain(text[last:start]))
        pieces.append(
            json.dumps(walk(value), ensure_ascii=False)
        )

        index = end
        last = end

    pieces.append(plain(text[last:]))
    return "".join(pieces)


def remove_secrets(text: str) -> str:
    if len(text) > MAX_INPUT:
        raise AIPrivacyError(
            "AI input exceeds the privacy processing limit."
        )

    return _transform(text, _strip_secrets)


class PrivacySession:

    def __init__(self, *, embedding: bool = False) -> None:
        self.embedding = embedding
        self.nonce = secrets.token_hex(12)
        self.mapping: dict[str, str] = {}
        self.tokens: dict[tuple[str, str], str] = {}
        self._names: set[str] = set()
        self._identifiers: set[str] = set()
        self._secrets: set[str] = set()

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

    @staticmethod
    def _literal(value: str) -> re.Pattern[str]:
        left = r"(?<!\w)" if re.match(r"\w", value[0]) else ""
        right = r"(?!\w)" if re.match(r"\w", value[-1]) else ""

        return re.compile(
            left + re.escape(value) + right
        )

    def _remember(
        self,
        target: set[str],
        value: str,
    ) -> None:
        value = value.strip()

        if (
            not value
            or value in {"None", "Not provided", REMOVED}
            or REMOVED in value
        ):
            return

        target.add(value)

        if (
            len(self._names | self._identifiers | self._secrets)
            > MAX_KNOWN_VALUES
        ):
            raise AIPrivacyError(
                "AI input exceeds the known-value privacy limit."
            )

    def _remember_secret(
        self,
        value: Any,
        depth: int = 0,
    ) -> None:
        if depth > MAX_DEPTH:
            raise AIPrivacyError(
                "AI input exceeds the privacy nesting limit."
            )

        if isinstance(value, str):
            self._remember(self._secrets, value)
            self._discover_secrets(value)

        elif isinstance(value, list):
            for item in value:
                self._remember_secret(item, depth + 1)

        elif isinstance(value, dict):
            for item in value.values():
                self._remember_secret(item, depth + 1)

    def _discover_secrets(self, value: str) -> None:
        for match in AUTH_TOKEN.finditer(value):
            self._remember(
                self._secrets,
                match.group().split(None, 1)[1],
            )

        for pattern in SECRET_SIGNATURES:
            for match in pattern.finditer(value):
                self._remember(
                    self._secrets,
                    match.group(),
                )

        for match in PRIVATE_KEY.finditer(value):
            self._remember(
                self._secrets,
                match.group(),
            )

        for match in HEADER.finditer(value):
            header_value = (
                match.group()
                .partition(":")[2]
                .strip()
            )

            self._remember(
                self._secrets,
                header_value,
            )

            for part in header_value.split(";"):
                if "=" in part:
                    self._remember(
                        self._secrets,
                        part.split("=", 1)[1]
                        .strip()
                        .strip("\"'"),
                    )

        for match in SECRET_ASSIGNMENT.finditer(value):
            secret = (
                match.group()[len(match.group(1)):]
                .strip()
            )

            if (
                len(secret) >= 2
                and secret[0] == secret[-1]
                and secret[0] in "\"'"
            ):
                secret = secret[1:-1]

            self._remember(self._secrets, secret)

    def _discover(self, value: str) -> str:
        self._discover_secrets(value)
        clean = _strip_secrets(value)

        for match in LABEL.finditer(clean):
            self._remember(
                self._names,
                match.group(2),
            )

        for part in re.split(r"\\[nrt]", clean):
            for pattern in (URL, EMAIL):
                for match in pattern.finditer(part):
                    self._remember(
                        self._identifiers,
                        match.group(),
                    )

            for match in IP.finditer(part):
                candidate = match.group().rstrip(".")

                try:
                    ipaddress.ip_address(candidate)
                except ValueError:
                    continue

                self._remember(
                    self._identifiers,
                    candidate,
                )

            for match in HOST.finditer(part):
                candidate = match.group()

                try:
                    labels = (
                        candidate.encode("idna")
                        .decode("ascii")
                        .split(".")
                    )
                except UnicodeError:
                    continue

                if (
                    labels[-1].isalpha()
                    or labels[-1].startswith("xn--")
                ):
                    self._remember(
                        self._identifiers,
                        candidate,
                    )

        return value


    def protect(self, text: str) -> str:
        return self.protect_many(text)[0]


    def protect_many(self, *texts: str) -> tuple[str, ...]:
        if any(len(text) > MAX_INPUT for text in texts):
            raise AIPrivacyError(
                "AI input exceeds the privacy processing limit."
            )

        if (
            len(texts) > 128
            or sum(map(len, texts)) > MAX_INPUT * 2
        ):
            raise AIPrivacyError(
                "AI request exceeds the privacy processing limit."
            )

        for text in texts:
            _transform(
                text,
                self._discover,
                on_name=lambda name: self._remember(
                    self._names,
                    name,
                ),
                on_secret=self._remember_secret,
            )

        def protect_plain(value: str) -> str:
            value = _strip_secrets(value)

            for secret in sorted(
                self._secrets,
                key=len,
                reverse=True,
            ):
                value = self._literal(secret).sub(
                    lambda match: REMOVED,
                    value,
                )

            for name in sorted(
                self._names,
                key=len,
                reverse=True,
            ):
                value = self._literal(name).sub(
                    lambda match: self.token("NAME", name),
                    value,
                )

            pieces = re.split(r"(\\[nrt])", value)

            for index in range(0, len(pieces), 2):
                part = URL.sub(self._url, pieces[index])

                part = EMAIL.sub(
                    lambda match: self.token(
                        "EMAIL",
                        match.group(),
                    ),
                    part,
                )

                part = IP.sub(self._ip, part)
                pieces[index] = HOST.sub(self._host, part)

            return "".join(pieces)

        protected = tuple(
            _transform(text, protect_plain)
            for text in texts
        )

        self.validate_outbound(*protected)
        return protected

    def validate_outbound(self, *texts: str) -> None:
        marker = re.compile(
            r"__PF_[A-Za-z0-9_]+__"
        )

        embedding_marker = re.compile(
            r"\[(?:NAME|HOST|EMAIL|IP|URL|"
            r"SECRET_REMOVED|URL_REMOVED)\]"
        )

        known = [
            self._literal(value)
            for value in (
                self._names
                | self._identifiers
                | self._secrets
            )
        ]

        def hide_marker(match: re.Match[str]) -> str:
            if match.group() not in self.mapping:
                raise AIPrivacyError(
                    "Unknown privacy marker in outbound AI input."
                )

            return " "

        def check(value: str) -> str:
            if _strip_secrets(value) != value:
                raise AIPrivacyError(
                    "AI outbound privacy validation failed."
                )

            visible = embedding_marker.sub(
                " ",
                marker.sub(hide_marker, value),
            )

            if any(
                pattern.search(visible)
                for pattern in known
            ):
                raise AIPrivacyError(
                    "AI outbound privacy validation failed."
                )

            return value

        def check_secret(value: Any) -> None:
            if value != REMOVED:
                raise AIPrivacyError(
                    "AI outbound privacy validation failed."
                )

        for text in texts:
            _transform(
                text,
                check,
                on_secret=check_secret,
                allow_markers=True,
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
        value = match.group()
        candidate = value.rstrip(".")

        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            return value

        return (
            self.token("IP", candidate)
            + value[len(candidate):]
        )

    def _host(self, match: re.Match[str]) -> str:
        value = match.group()

        try:
            labels = (
                value.encode("idna")
                .decode("ascii")
                .split(".")
            )
        except UnicodeError:
            return value

        if not (
            labels[-1].isalpha()
            or labels[-1].startswith("xn--")
        ):
            return value

        return self.token("HOST", value)
    

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
                    pattern.sub(replace, key): walk(item)
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