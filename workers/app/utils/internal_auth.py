import os

INTERNAL_WEBHOOK_SECRET = os.environ.get(
    "INTERNAL_WEBHOOK_SECRET",
    "",
)

if len(INTERNAL_WEBHOOK_SECRET.encode("utf-8")) < 32:
    raise RuntimeError(
        "INTERNAL_WEBHOOK_SECRET must contain at least 32 bytes"
    )


def internal_headers() -> dict[str, str]:
    return {
        "X-Internal-Token": INTERNAL_WEBHOOK_SECRET,
        "Content-Type": "application/json",
    }