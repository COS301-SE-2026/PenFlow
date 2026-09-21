import re
from uuid import UUID

from app.schemas.assistant import (
    AssistantQueryRequest,
    SecurityQueryIntent,
)
from app.services.assistant_conversation import (
    build_routing_text,
)


class SecurityQueryRouter:
    CVE_PATTERN = re.compile(
        r"\bcve-\d{4}-\d{4,7}\b",
        re.IGNORECASE,
    )

    UUID_PATTERN = re.compile(
        (
            r"\b[0-9a-f]{8}-"
            r"[0-9a-f]{4}-"
            r"[1-5][0-9a-f]{3}-"
            r"[89ab][0-9a-f]{3}-"
            r"[0-9a-f]{12}\b"
        ),
        re.IGNORECASE,
    )

    EXACT_LOOKUP_PHRASES = (
        "finding id",
        "exact finding",
        "specific finding",
        "this cve",
        "that cve",
    )

    COMPARISON_PHRASES = (
        "compare scans",
        "compare this scan",
        "previous scan",
        "prior scan",
        "last scan",
        "changed since",
        "change since",
        "improved since",
        "worse since",
        "better since",
        "new findings",
        "new vulnerabilities",
        "resolved findings",
        "resolved vulnerabilities",
        "findings are new",
        "findings were resolved",
        "vulnerabilities are new",
        "vulnerabilities were resolved",
    )

    PORTFOLIO_PHRASES = (
        "across my scans",
        "across all scans",
        "across my domains",
        "all my domains",
        "which domain",
        "overall security posture",
        "portfolio",
        "recurring findings",
        "recurring vulnerabilities",
        "keep coming back",
        "keeps coming back",
        "prioritize this week",
        "priority this week",
        "which of my domains",
    )

    RISK_PRIORITIZATION_PHRASES = (
        "what should i fix first",
        "what should i remediate first",
        "what should be remediated first",
        "what should i address first",
        "which should i address first",
        "highest risk",
        "highest-risk",
        "top risk",
        "most critical",
        "most severe",
        "worst finding",
        "priority finding",
        "prioritize",
        "prioritise",
        "remediation priority",
    )

    SUMMARY_PHRASES = (
        "summarize this scan",
        "summarise this scan",
        "scan summary",
        "overview of this scan",
        "security overview",
        "what did this scan find",
        "what was found",
        "how secure is",
        "summary of this scan",
    )


    @classmethod
    def classify(
        cls,
        request: AssistantQueryRequest,
    ) -> SecurityQueryIntent:
        question = build_routing_text(
            request
        ).casefold()

        if (
            cls.CVE_PATTERN.search(question)
            or cls.UUID_PATTERN.search(question)
            or any(
                phrase in question
                for phrase in cls.EXACT_LOOKUP_PHRASES
            )
        ):
            return SecurityQueryIntent.EXACT_LOOKUP

        if any(
            phrase in question
            for phrase in cls.COMPARISON_PHRASES
        ):
            return SecurityQueryIntent.SCAN_COMPARISON

        if any(
            phrase in question
            for phrase in cls.PORTFOLIO_PHRASES
        ):
            return SecurityQueryIntent.PORTFOLIO_ANALYSIS

        if any(
            phrase in question
            for phrase in cls.RISK_PRIORITIZATION_PHRASES
        ):
            return SecurityQueryIntent.RISK_PRIORITIZATION

        if any(
            phrase in question
            for phrase in cls.SUMMARY_PHRASES
        ):
            return SecurityQueryIntent.SCAN_SUMMARY

        return SecurityQueryIntent.SEMANTIC_SEARCH


    @classmethod
    def extract_finding_id(
        cls,
        request: AssistantQueryRequest,
    ) -> UUID | None:
        question = build_routing_text(request)
        match = cls.UUID_PATTERN.search(question)

        if match is None:
            return None

        return UUID(match.group(0))


    @classmethod
    def extract_cve_id(
        cls,
        request: AssistantQueryRequest,
    ) -> str | None:
        question = build_routing_text(request)
        match = cls.CVE_PATTERN.search(question)

        if match is None:
            return None

        return match.group(0).upper()
