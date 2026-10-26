import socket
import ssl
from http.cookies import CookieError, SimpleCookie
from ipaddress import ip_address, ip_network
from time import monotonic
from urllib.parse import urljoin, urlsplit, urlunsplit

import certifi
import dns.exception
import dns.resolver
import idna
import requests
import urllib3
from requests.structures import CaseInsensitiveDict
from urllib3.exceptions import HTTPError


class UnsafeDestination(requests.RequestException):
    pass


_DENIED_NETWORKS = tuple(
    ip_network(value)
    for value in (
        "168.63.129.16/32",
        "64:ff9b::/96",
        "64:ff9b:1::/48",
        "2002::/16",     
        "2001::/32",        
    )
)


def public_ip(value: str) -> str:
    if "%" in value:
        raise UnsafeDestination(
            "Scoped IP addresses are not permitted"
        )

    try:
        address = ip_address(value)

    except ValueError as exc:
        raise UnsafeDestination(
            "A single IP address is required"
        ) from exc

    if (
        not address.is_global
        or address.is_multicast
        or address.is_reserved
        or getattr(address, "ipv4_mapped", None) is not None
        or any(
            address in network
            for network in _DENIED_NETWORKS
        )
    ):
        raise UnsafeDestination(
            "Non-public destination is not permitted"
        )

    return str(address)


def normalise_host(value: str) -> str:
    if (
        not value
        or value != value.strip()
        or any(c in value for c in "/\\@?#%")
    ):
        raise UnsafeDestination("Invalid target hostname")

    value = value.rstrip(".")

    try:
        ip_address(value)
    except ValueError:
        try:
            value = idna.encode(
                value,
                uts46=True,
                std3_rules=True,
            ).decode("ascii")
        except idna.IDNAError as exc:
            raise UnsafeDestination(
                "Invalid target hostname"
            ) from exc

        if "." not in value or len(value) > 253:
            raise UnsafeDestination(
                "A public hostname is required"
            )

        return value.lower()

    return public_ip(value)


def resolve_public_host(
        host: str,
        timeout: float = 5.0,
) -> list[str]:
    host = normalise_host(host)

    try:
        ip_address(host)
    except ValueError:
        pass
    else:
        return [public_ip(host)]

    deadline = monotonic() + timeout
    resolver = dns.resolver.Resolver()
    addresses: list[str] = []

    for record_type in ("A", "AAAA"):
        remaining = deadline - monotonic()

        if remaining <= 0:
            raise UnsafeDestination(
                "DNS resolution timed out"
            )

        try:
            answers = resolver.resolve(
                host,
                record_type,
                lifetime=remaining,
                search=False,
            )

        except dns.resolver.NoAnswer:
            continue
        except dns.exception.DNSException as exc:
            raise UnsafeDestination(
                "Target DNS could not be validated"
            ) from exc

        for record in answers:
            address = public_ip(record.to_text())

            if address not in addresses:
                addresses.append(address)

    if not addresses:
        raise UnsafeDestination(
            "Target has no public addresses"
        )

    return addresses


def _parse_url(url: str) -> tuple[str, str, int]:
    if "\\" in url or any(
        ord(c) <= 32 or ord(c) == 127
        for c in url
    ):
        raise UnsafeDestination("Invalid target URL")

    try:
        parts = urlsplit(url)

        if (
            parts.scheme not in {"http", "https"}
            or parts.username is not None
        ):
            raise UnsafeDestination(
                "Only HTTP(S) URLs without credentials are permitted"
            )

        host = normalise_host(parts.hostname or "")
        port = (
            parts.port
            if parts.port is not None
            else (443 if parts.scheme == "https" else 80)
        )

        if not 1 <= port <= 65535:
            raise UnsafeDestination("Invalid target port")

    except ValueError as exc:
        raise UnsafeDestination(
            "Invalid target URL"
        ) from exc

    authority = f"[{host}]" if ":" in host else host
    authority = f"{authority}:{port}"

    clean = urlunsplit(
        (
            parts.scheme,
            authority,
            parts.path or "/",
            parts.query,
            "",
        )
    )

    prepared = requests.Request("GET", clean).prepare()

    if prepared.url is None:
        raise UnsafeDestination("Invalid target URL")

    return prepared.url, host, port


def _fetch_ip(
        url: str,
        host: str,
        port: int,
        address: str,
        timeout: float,
        verify: bool,
        max_bytes: int,
) -> requests.Response:
    parts = urlsplit(url)

    host_header = f"[{host}]" if ":" in host else host

    if port != (443 if parts.scheme == "https" else 80):
        host_header = f"{host_header}:{port}"

    headers = {
        "Host": host_header,
        "User-Agent": "PenFlow/1.0",
        "Accept-Encoding": "gzip, deflate",
    }

    limits = urllib3.Timeout(
        connect=min(3.0, timeout),
        read=min(3.0, timeout),
    )

    pool: urllib3.HTTPConnectionPool

    if parts.scheme == "https":
        pool = urllib3.HTTPSConnectionPool(
            address,
            port,
            server_hostname=host,
            assert_hostname=host if verify else False,
            cert_reqs=(
                ssl.CERT_REQUIRED
                if verify
                else ssl.CERT_NONE
            ),
            ca_certs=certifi.where() if verify else None,
            timeout=limits,
        )
    else:
        pool = urllib3.HTTPConnectionPool(
            address,
            port,
            timeout=limits,
        )

    raw = None
    deadline = monotonic() + timeout

    try:
        target = urlunsplit(
            ("", "", parts.path or "/", parts.query, "")
        )

        raw = pool.urlopen(
            "GET",
            target,
            headers=headers,
            redirect=False,
            retries=False,
            preload_content=False,
        )

        response = requests.Response()
        response.status_code = raw.status
        response.url = url
        response.headers = CaseInsensitiveDict(raw.headers)

        if raw.status in {301, 302, 303, 307, 308}:
            response._content = b""
            return response

        encoding = raw.headers.get(
            "Content-Encoding",
            "identity",
        ).lower().strip()

        if encoding not in {"identity", "gzip", "deflate"}:
            raise UnsafeDestination(
                "Unsupported response compression"
            )

        body = bytearray()

        while True:
            if monotonic() >= deadline:
                raise UnsafeDestination(
                    "Target response exceeded time budget"
                )

            chunk = raw.read1(
                min(65536, max_bytes + 1 - len(body)),
                decode_content=True,
            )

            if not chunk:
                break

            body.extend(chunk)

            if len(body) > max_bytes:
                raise UnsafeDestination(
                    "Target response exceeded size limit"
                )


        response._content = bytes(body)
        response.encoding = (
            requests.utils.get_encoding_from_headers(
                response.headers
            )
        )

        for header in raw.headers.getlist("Set-Cookie"):
            cookie = SimpleCookie()

            try:
                cookie.load(header)

                for name, morsel in cookie.items():
                    response.cookies.set(name, morsel.value)

            except CookieError:
                continue

        return response

    finally:
        if raw is not None:
            raw.close()

        pool.close()


def safe_get(
        url: str,
        *,
        timeout: float = 10.0,
        verify: bool = True,
        max_bytes: int = 2 * 1024 * 1024,
        max_redirects: int = 5,
        allowed_domain: str | None = None,
) -> requests.Response:
    if timeout <= 0 or max_bytes < 1 or max_redirects < 0:
        raise ValueError("Invalid outbound request limits")

    root = (
        normalise_host(allowed_domain)
        if allowed_domain is not None
        else None
    )
    deadline = monotonic() + timeout

    for hop in range(max_redirects + 1):
        url, host, port = _parse_url(url)

        if (
            root is not None
            and host != root
            and not host.endswith("." + root)
        ):
            raise UnsafeDestination("Redirect is outside authorised domain scope")

        remaining = deadline - monotonic()

        if remaining <= 0:
            raise UnsafeDestination(
                "Target request exceeded time budget"
            )

        addresses = resolve_public_host(
            host,
            timeout=remaining,
        )

        response = None

        for address in addresses:
            remaining = deadline - monotonic()

            if remaining <= 0:
                raise UnsafeDestination(
                    "Target request exceeded time budget"
                )

            try:
                response = _fetch_ip(
                    url,
                    host,
                    port,
                    address,
                    remaining,
                    verify,
                    max_bytes,
                )
                break

            except (HTTPError, OSError) as exc:
                if address == addresses[-1]:
                    raise requests.ConnectionError(
                        "Target connection failed"
                    ) from exc

        if response is None:
            raise UnsafeDestination(
                "Target has no usable public address"
            )

        if response.status_code not in {
            301, 302, 303, 307, 308
        }:
            return response

        location = response.headers.get("Location")

        if not location:
            return response

        if hop == max_redirects:
            raise UnsafeDestination(
                "Target exceeded redirect limit"
            )

        url = urljoin(url, location)

    raise UnsafeDestination("Target exceeded redirect limit")


def public_connection(
        host: str,
        port: int,
        timeout: float = 5.0,
) -> socket.socket:
    deadline = monotonic() + timeout
    addresses = resolve_public_host(host, timeout=timeout)

    for address in addresses:
        remaining = deadline - monotonic()

        if remaining <= 0:
            raise UnsafeDestination(
                "Target connection timed out"
            )

        try:
            return socket.create_connection(
                (address, port),
                timeout=remaining,
            )

        except OSError:
            if address == addresses[-1]:
                raise

    raise UnsafeDestination(
        "Target has no usable public address"
    )