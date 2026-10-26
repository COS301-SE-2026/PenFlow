import base64
import json
import resource
import sys
from pathlib import Path
from typing import Any

BASE_URL = "https://penflow-report.invalid/"

ALLOWED_NAMES = {
    "report_styles.css",
    "bluevision_logo.png",
    "brocode_logo.png",
    "scan-screenshot.png",
}

MAX_HTML_BYTES = 4 * 1024 * 1024
MAX_RESOURCE_BYTES = 8 * 1024 * 1024


class ResourceGuard:
    def __init__(self, assets: dict[str, bytes]) -> None:
        if not set(assets) <= ALLOWED_NAMES:
            raise ValueError("Unapproved report asset")

        self.assets = {
            BASE_URL + name: value
            for name, value in assets.items()
        }
        self.denied = False
        self.requests = 0
        self.total_bytes = 0

    def __call__(
            self,
            url: str,
            *args: Any,
            **kwargs: Any,
    ) -> dict[str, Any]:
        self.requests += 1
        contents = self.assets.get(url)

        if contents is not None:
            self.total_bytes += len(contents)

        if (
            contents is None
            or len(contents) > MAX_RESOURCE_BYTES
            or self.requests > 100
            or self.total_bytes > 32 * 1024 * 1024
        ):
            self.denied = True
            raise ValueError("Report resource rejected")

        mime_type = (
            "text/css"
            if url.endswith(".css")
            else "image/png"
        )

        return {
            "string": contents,
            "mime_type": mime_type,
            "redirected_url": url,
        }


def render(
        html: str,
        assets: dict[str, bytes],
        output: Path,
) -> None:
    from weasyprint import CSS, HTML
    from weasyprint.urls import (
        FatalURLFetchingError,
        URLFetcher,
        URLFetcherResponse,
    )

    if len(html.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError("Report HTML exceeds size limit")

    guard = ResourceGuard(assets)

    class BundledAssetFetcher(URLFetcher):  #type: ignore[misc]
        def fetch(
            self,
            url: str,
            headers: Any = None,
        ) -> URLFetcherResponse:
            result = guard(url)

            return URLFetcherResponse(
                url=url,
                body=result["string"],
                headers={
                    "Content-Type": result["mime_type"],
                },
            )

    fetcher = BundledAssetFetcher(
        allow_redirects=False,
        fail_on_errors=True,
    )

    try:
        stylesheet = CSS(
            string=assets["report_styles.css"].decode("utf-8"),
            base_url=BASE_URL,
            url_fetcher=fetcher,
        )

        HTML(
            string=html,
            base_url=BASE_URL,
            url_fetcher=fetcher,
        ).write_pdf(
            str(output),
            stylesheets=[stylesheet],
            presentational_hints=False,
        )

    except (Exception, FatalURLFetchingError) as exc:
        output.unlink(missing_ok=True)

        if guard.denied:
            raise ValueError(
                "Report attempted prohibited resource access"
            ) from exc

        raise

    if guard.denied:
        output.unlink(missing_ok=True)
        raise ValueError(
            "Report attempted prohibited resource access"
        )


def main() -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(
        resource.RLIMIT_AS,
        (768 * 1024 * 1024,) * 2,
    )
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(
        resource.RLIMIT_FSIZE,
        (32 * 1024 * 1024,) * 2,
    )

    payload = sys.stdin.buffer.read(
        40 * 1024 * 1024 + 1
    )

    if len(payload) > 40 * 1024 * 1024:
        raise ValueError("Report payload exceeds size limit")

    data = json.loads(payload)

    assets = {
        name: base64.b64decode(value, validate=True)
        for name, value in data["assets"].items()
    }

    render(
        data["html"],
        assets,
        Path(sys.argv[1]),
    )


if __name__ == "__main__":
    main()