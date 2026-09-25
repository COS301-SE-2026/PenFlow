import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from pydantic import ValidationError

from app.schemas.assistant_generation import AssistantGeneratedFindingAnswer

FINDING_ID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}\b"
)

FINDING_CITATION_PATTERN = re.compile(
    r"\[Finding ID:\s*"
    r"([0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12})\s*\]",
    re.IGNORECASE,
)

CVE_PATTERN = re.compile(
    r"\bCVE-\d{4}-\d{4,7}\b",
    re.IGNORECASE,
)

CVSS_PATTERN = re.compile(
    r"\bCVSS"
    r"(?:\s+score)?"
    r"(?:\s+(?:is|of))?"
    r"\s*[:=]?\s*"
    r"(10(?:\.0)?|[0-9](?:\.\d)?)\b",
    re.IGNORECASE,
)

SEVERITY_PATTERN = re.compile(
    r"(?:"
    r"\bseverity(?:\s+(?:is|of))?\s*[:=]?\s*"
    r"(critical|high|medium|low|info|informational)\b"
    r"|"
    r"\b(critical|high|medium|low|info|informational)"
    r"[-\s]+severity\b"
    r")",
    re.IGNORECASE,
)

ABSOLUTE_URL_PATTERN = re.compile(
    r"\bhttps?://[^\s<>\])]+",
    re.IGNORECASE,
)

INTERNAL_PATH_PATTERN = re.compile(
    r"(?<![\w:])"
    r"/(?:[A-Za-z0-9._~-]+"
    r"(?:/[A-Za-z0-9._~-]+)*)"
    r"(?:\?[A-Za-z0-9._~!$&'()*+,;=@%/?-]*)?"
)

class AssistantAnswerValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AssistantFindingEvidence:
    finding_id: UUID
    severity: str
    cvss_score: float | None = None
    cves: tuple[str, ...] = ()


class AssistantAnswerValidator:
    @staticmethod
    def parse_structured_output(
        raw_output: str,
    ) -> AssistantGeneratedFindingAnswer:
        normalized = raw_output.strip()

        if normalized.startswith("```"):
            lines = normalized.splitlines()

            if (
                len(lines) >= 3
                and lines[0].strip().casefold()
                in {"```", "```json"}
                and lines[-1].strip() == "```"
            ):
                normalized = "\n".join(lines[1:-1]).strip()

        try:
            payload = json.loads(normalized)

        except json.JSONDecodeError as exc:
            raise AssistantAnswerValidationError(
                "This model did not return valid structured JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise AssistantAnswerValidationError(
                "The structured generation must be a JSON object."
            ) 

        try:
            return (AssistantGeneratedFindingAnswer.model_validate(payload))

        except ValidationError as exc:
            raise AssistantAnswerValidationError(
                "The model returned an invalid answer structure."
            ) from exc


    @staticmethod
    def normalize_cves(
        values: Iterable[str],
    ) -> set[str]:
        return {
            value.strip().upper()
            for value in values
            if value and value.strip()
        }


    @staticmethod
    def normalize_severity(
        value: str,
    ) -> str:
        normalized = value.strip().casefold()

        if normalized == "informational":
            return "info"

        return normalized


    @staticmethod
    def cvss_equal(
        first: float,
        second: float,
    ) -> bool:
        return abs(float(first) - float(second)) < 0.05


    @staticmethod
    def validate_links(
        links: Iterable[str],
        allowed_links: set[str],
    ) -> None:
        for link in links:
            if (
                not link.startswith("/")
                or link.startswith("//")
                or "\\" in link
                or "\r" in link
                or "\n" in link
                or link not in allowed_links
            ):
                raise AssistantAnswerValidationError(
                    "The generated answer referenced an "
                    "unauthorized URL."
                )


    @staticmethod
    def extract_finding_ids(answer: str) -> set[UUID]:
        return {
            UUID(match.group(0))
            for match in FINDING_ID_PATTERN.finditer(answer)
        }


    @staticmethod
    def extract_finding_citations(
        answer: str,
    ) -> set[UUID]:
        return {
            UUID(match.group(1))
            for match in FINDING_CITATION_PATTERN.finditer(answer)
        }


    @staticmethod
    def extract_cves(answer: str) -> set[str]:
        return {
            match.group(0).upper()
            for match in CVE_PATTERN.finditer(answer)
        }


    @staticmethod
    def extract_cvss_scores(
        answer: str,
    ) -> set[float]:
        return {
            float(match.group(1))
            for match in CVSS_PATTERN.finditer(answer)
        }


    @classmethod
    def extract_severities(
        cls,
        answer: str,
    ) -> set[str]:
        return {
            cls.normalize_severity(
                match.group(1) or match.group(2)
            )
            for match in SEVERITY_PATTERN.finditer(answer)
        }


    @staticmethod
    def extract_answer_links(
        answer: str
    ) -> set[str]:
        if ABSOLUTE_URL_PATTERN.search(answer):
            raise AssistantAnswerValidationError(
                "The generated answer included an external URL."
            )

        return {
            match.group(0).rstrip(".,;:")
            for match in INTERNAL_PATH_PATTERN.finditer(answer)
        }


    @classmethod
    def validate_structured(
        cls,
        *,
        raw_output: str,
        evidence: Iterable[AssistantFindingEvidence],
        allowed_entity_ids: Iterable[UUID] = (),
        allowed_links: Iterable[str] = (),
        require_finding_citation: bool = True,
    ) -> AssistantGeneratedFindingAnswer:
        generated = cls.parse_structured_output(raw_output)

        evidence_by_id = {
            item.finding_id: item
            for item in evidence
        }

        allowed_finding_ids = set(evidence_by_id)
        allowed_entity_id_set = (
            set(allowed_entity_ids) | allowed_finding_ids
        )

        allowed_link_set = set(allowed_links)

        cited_ids = set(generated.cited_finding_ids)

        if (
            len(cited_ids)
            != len(generated.cited_finding_ids)
        ):
            raise AssistantAnswerValidationError(
                "The generated answer contained duplicate citations."
            )

        if not cited_ids.issubset(allowed_finding_ids):
            raise AssistantAnswerValidationError(
                "The generated answer cited findings "
                "outside the authorized evidence."
            )

        answer_citations = (
            cls.extract_finding_citations(generated.answer)
        )

        if answer_citations != cited_ids:
            raise AssistantAnswerValidationError(
                "The structured citations did not match "
                "the citations in the answer."
            )

        if (
            require_finding_citation
            and allowed_finding_ids
            and not generated.insufficient_evidence
            and not cited_ids
        ):
            raise AssistantAnswerValidationError(
                "The generated answer did not cite its finding evidence."
            )

        if generated.insufficient_evidence:
            if (
                cited_ids
                or generated.claims
                or generated.links
            ):
                raise AssistantAnswerValidationError(
                    "An insufficient-evidence answer cannot "
                    "contain generated claims, citations, or links."
                )

            if cls.extract_finding_ids(generated.answer):
                raise AssistantAnswerValidationError(
                    "An insufficient-evidence answer cannot "
                    "contain entity identifiers."
                )

            if cls.extract_cves(generated.answer):
                raise AssistantAnswerValidationError(
                    "An insufficient-evidence answer cannot "
                    "contain CVE claims."
                )

            if cls.extract_cvss_scores(generated.answer):
                raise AssistantAnswerValidationError(
                    "An insufficient-evidence answer cannot "
                    "contain CVSS claims."
                )

            if cls.extract_severities(generated.answer):
                raise AssistantAnswerValidationError(
                    "An insufficient-evidence answer cannot "
                    "contain severity claims."
                )

            if cls.extract_answer_links(generated.answer):
                raise AssistantAnswerValidationError(
                    "An insufficient-evidence answer cannot "
                    "contain URLs."
                )

            return generated

        referenced_ids = cls.extract_finding_ids(generated.answer)

        if not referenced_ids.issubset(allowed_entity_id_set):
            raise AssistantAnswerValidationError(
                "The generated answer referenced an "
                "unauthorized entity identifier."
            )

        cls.validate_links(
            links=[
                *generated.links,
                *cls.extract_answer_links(generated.answer),
            ],
            allowed_links=allowed_link_set,
        )

        claim_ids = [
            claim.finding_id
            for claim in generated.claims
        ]

        if len(set(claim_ids)) != len(claim_ids):
            raise AssistantAnswerValidationError(
                "The generated answer contained duplicate "
                "finding claims."
            )

        if set(claim_ids) != cited_ids:
            raise AssistantAnswerValidationError(
                "Every cited finding must have exactly one "
                "structured claim."
            )

        for claim in generated.claims:
            trusted = evidence_by_id.get(claim.finding_id)

            if trusted is None:
                raise AssistantAnswerValidationError(
                    "A structured claim referenced a finding "
                    "outside the authorized evidence."
                )

            expected_severity = (
                cls.normalize_severity(trusted.severity)
            )

            if (
                claim.severity is not None
                and cls.normalize_severity(claim.severity)
                != expected_severity
            ):
                raise AssistantAnswerValidationError(
                    "A generated severity claim did not "
                    "match the stored finding."
                )

            if claim.cvss_score is not None:
                if (
                    trusted.cvss_score is None
                    or not cls.cvss_equal(
                        claim.cvss_score,
                        trusted.cvss_score,
                    )
                ):
                    raise AssistantAnswerValidationError(
                        "A generated CVSS claim did not "
                        "match the stored finding."
                    )

            trusted_cves = cls.normalize_cves(trusted.cves)
            claim_cves = cls.normalize_cves(claim.cves)

            if not claim_cves.issubset(trusted_cves):
                raise AssistantAnswerValidationError(
                    "A generated CVE claim did not "
                    "match the stored finding."
                )

        allowed_cves = {
            cve
            for item in evidence_by_id.values()
            for cve in cls.normalize_cves(item.cves)
        }

        if not cls.extract_cves(generated.answer).issubset(
            allowed_cves
        ):
            raise AssistantAnswerValidationError(
                "The generated answer referenced an "
                "unsupported CVE."
            )

        allowed_cvss_scores = {
            float(item.cvss_score)
            for item in evidence_by_id.values()
            if item.cvss_score is not None
        }

        for score in cls.extract_cvss_scores(generated.answer):
            if not any(
                cls.cvss_equal(
                    score,
                    allowed_score,
                )
                for allowed_score in allowed_cvss_scores
            ):
                raise AssistantAnswerValidationError(
                    "The generated answer referenced an "
                    "unsupported CVSS score."
                )

        allowed_severities = {
            cls.normalize_severity(item.severity)
            for item in evidence_by_id.values()
        }

        if not cls.extract_severities(generated.answer).issubset(
            allowed_severities
        ):
            raise AssistantAnswerValidationError(
                "The generated answer referenced an "
                "unsupported severity."
            )

        return generated