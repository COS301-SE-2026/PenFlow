import logging
from typing import Literal

logger = logging.getLogger(__name__)

ValidationFailureReason = Literal[
    "empty_generation",
    "unsupported_reference",
]


def record_validation_failure(
        reason: ValidationFailureReason,
) -> None:
    logger.warning(
        "assistant_answer_validation "
        "outcome=rejected reason=%s count=1",
        reason,
    )
