from app.schemas.assistant import (
    AssistantCapability,
    AssistantQueryRequest,
)


class AssistantRouter:
    NAVIGATION_PHRASES = (
        "where do i",
        "where can i",
        "take me to",
        "navigate to",
        "which page",
        "where is the",
        "open the page",
    )

    USER_DATA_PHRASES = (
        "my next scan",
        "next scheduled scan",
        "my upcoming scan",
        "my scan schedule",
        "when is my",
        "my latest scan",
        "my most recent scan",
        "my unverified domains",
        "my unread notifications",
        "status of my engagement",
        "my available reports",
        "my recent scans",
        "my scans",
        "scans have i run",
        "my domains",
        "how many domains",
        "domains do i have",
        "my notifications",
        "my engagements",
        "my reports",
        "available reports",
        "reports are available",
        "unread notifications",
        "this engagement",
        "engagements require attention",
        "engagements need attention",
        "engagements need scheduling",
        "engagements awaiting review",
        "engagements assigned to me",
        "what should i work on next",
        "my pentest",
        "my retest",
        "engagement report",
        "which engagements",
        "engagements are",
        "no pentester",
        "who is assigned",
        "open retest",
        "my report",
    )

    PRODUCT_TERMS = (
        "penflow",
        "active scan",
        "active scanning",
        "passive ctem",
        "domain verification",
        "verify a domain",
        "scheduled scan",
        "scan schedule",
        "retest",
        "pentest engagement",
        "security report",
        "add a domain",
        "manage domains",
        "verify domain",
        "start a scan",
        "run a scan",
        "passive reconnaissance",
        "scan history",
        "scan results",
        "security analyst",
        "download report",
        "email report",
        "request an engagement",
        "request a pentest",
        "penetration test",
        "rules of engagement",
    )

    SECURITY_TERMS = (
        "finding",
        "findings",
        "vulnerability",
        "vulnerabilities",
        "risk",
        "risks",
        "remediate",
        "remediation",
        "cve",
        "cvss",
        "exposure",
        "authentication weakness",
        "sql injection",
        "security issue",
    )

    PORTFOLIO_SECURITY_PHRASES = (
        "across my scans",
        "across all scans",
        "across my domains",
        "overall security posture",
        "portfolio",
        "recurring findings",
        "recurring vulnerabilities",
        "keep coming back",
        "keeps coming back",
        "prioritize this week",
        "priority this week",
    )

    PORTFOLIO_DOMAIN_PHRASES = (
        "all my domains",
        "which domain",
        "which of my domains",
    )

    CONTINUABLE_CAPABILITIES = {
        AssistantCapability.PRODUCT_HELP,
        AssistantCapability.NAVIGATION,
        AssistantCapability.USER_DATA,
    }


    @classmethod
    def is_portfolio_security_question(
        cls,
        question: str,
    ) -> bool:
        if any(
            phrase in question
            for phrase in cls.PORTFOLIO_SECURITY_PHRASES
        ):
            return True

        has_domain_scope = any(
            phrase in question
            for phrase in cls.PORTFOLIO_DOMAIN_PHRASES
        )

        has_security_subject = any(
            term in question
            for term in cls.SECURITY_TERMS
        )

        return has_domain_scope and has_security_subject


    @classmethod
    def classify(
        cls,
        request: AssistantQueryRequest,
    ) -> AssistantCapability:
        question = request.question.casefold()
        context = request.context

        if any(
            phrase in question
            for phrase in cls.NAVIGATION_PHRASES
        ):
            return AssistantCapability.NAVIGATION

        if cls.is_portfolio_security_question(question):
            return AssistantCapability.SECURITY_ANALYSIS
        
        if any(
            phrase in question
            for phrase in cls.USER_DATA_PHRASES
        ):
            return AssistantCapability.USER_DATA

        if any(
            term in question
            for term in cls.PRODUCT_TERMS
        ):
            return AssistantCapability.PRODUCT_HELP

        if context.finding_id is not None:
            return AssistantCapability.FINDING_EXPLANATION

        if context.scan_id is not None:
            return AssistantCapability.SECURITY_ANALYSIS

        if context.engagement_id is not None:
            return AssistantCapability.USER_DATA

        if any(
            term in question
            for term in cls.SECURITY_TERMS
        ):
            return AssistantCapability.SECURITY_ANALYSIS

        if (
            request.history
            and request.previous_capability
            in cls.CONTINUABLE_CAPABILITIES
        ):
            return request.previous_capability

        return AssistantCapability.UNSUPPORTED

        