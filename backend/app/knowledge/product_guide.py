from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GuideLink:
    label: str
    href: str


@dataclass(frozen=True, slots=True)
class GuideArticle:
    slug: str
    title: str
    content: str
    keywords: tuple[str, ...]
    links: tuple[GuideLink, ...]


PRODUCT_GUIDE: tuple[GuideArticle, ...] = (
    GuideArticle(
        slug="penflow-overview",
        title="What PenFlow does",
        content=(
            "PenFlow helps users manage domains, run active vulnerability "
            "scans or passive reconnaissance, schedule recurring scans, "
            "review scan results and findings, generate reports, and manage "
            "penetration-testing engagements. Active scanning requires a "
            "verified domain. Passive reconnaissance uses public information "
            "and does not require domain ownership verification."
        ),
        keywords=(
            "penflow",
            "what can penflow do",
            "features",
            "capabilities",
            "getting started",
            "overview",
        ),
        links=(
            GuideLink(label="Open PenFlow", href="/"),
            GuideLink(label="View domains", href="/domains"),
            GuideLink(label="Start a scan", href="/phase2_scan"),
        ),
    ),
    GuideArticle(
        slug="domain-management",
        title="Adding and verifying domains",
        content=(
            "Open Domains and add the domain name without a URL path. "
            "Passive monitoring can begin immediately. Before active scans "
            "are available, PenFlow requires proof of ownership. Open the "
            "domain details, copy the displayed verification token into a "
            "DNS TXT record at the domain root, wait for DNS propagation, "
            "and select Verify now. DNS changes can take up to 24 hours to "
            "propagate. The Domains page shows pending, verified, and failed "
            "verification states."
        ),
        keywords=(
            "domain",
            "add domain",
            "verify domain",
            "domain verification",
            "dns txt",
            "txt record",
            "ownership verification",
            "verification failed",
        ),
        links=(
            GuideLink(label="Manage domains", href="/domains"),
        ),
    ),
    GuideArticle(
        slug="running-scans",
        title="Running active and passive scans",
        content=(
            "Open Scans and choose Active or Passive. Active Vulnerability "
            "Scan performs direct testing and can only target one of the "
            "user's verified domains. Passive Reconnaissance uses public "
            "records and accepts a domain without ownership verification. "
            "After a scan starts, PenFlow shows its progress and makes its "
            "results available when processing completes."
        ),
        keywords=(
            "scan",
            "start scan",
            "run scan",
            "active scan",
            "active vulnerability",
            "passive scan",
            "passive reconnaissance",
            "passive ctem",
            "verified target",
        ),
        links=(
            GuideLink(label="Start a scan", href="/phase2_scan"),
            GuideLink(label="Verify a domain", href="/domains"),
        ),
    ),
    GuideArticle(
        slug="scheduled-scans",
        title="Creating and managing scheduled scans",
        content=(
            "Scheduled scans are recurring active vulnerability scans for "
            "verified domains. A schedule can run weekly or monthly in the "
            "selected timezone. The Scheduled Scans page displays the next "
            "and previous run times. Existing schedules can be edited, "
            "paused, resumed, or deleted. A paused schedule retains its "
            "configuration but does not create scans."
        ),
        keywords=(
            "scheduled scan",
            "scan schedule",
            "recurring scan",
            "weekly scan",
            "monthly scan",
            "pause schedule",
            "next scan",
            "automatic scan",
        ),
        links=(
            GuideLink(
                label="View scheduled scans",
                href="/scheduled-scans",
            ),
            GuideLink(label="Manage domains", href="/domains"),
        ),
    ),
    GuideArticle(
        slug="scan-results",
        title="Reviewing scan results, findings, and reports",
        content=(
            "Completed scans are available from Scan History. A scan result "
            "contains an overview plus assets, services, findings, activity, "
            "and Security Analyst views. Findings contain severity, affected "
            "asset or service information, available evidence, and remediation "
            "guidance. Scan History also provides access to the generated PDF "
            "report and the option to email a report."
        ),
        keywords=(
            "scan history",
            "old scans",
            "previous scans",
            "scan result",
            "findings",
            "assets",
            "services",
            "activity",
            "security analyst",
            "report",
            "pdf report",
            "email report",
        ),
        links=(
            GuideLink(label="Open scan history", href="/history"),
        ),
    ),
    GuideArticle(
        slug="pentesting-engagements",
        title="Penetration-testing engagements",
        content=(
            "A penetration-testing engagement request records the assessment "
            "type, objective, dates, rules of engagement, and every domain, "
            "IP address, hostname, or URL that is in scope. Live engagement "
            "pages are used to follow engagement progress and the related "
            "communication, findings, and retest activity available to the "
            "current user's role."
        ),
        keywords=(
            "pentest",
            "penetration test",
            "engagement",
            "request engagement",
            "scope",
            "rules of engagement",
            "retest",
            "live engagement",
        ),
        links=(
            GuideLink(
                label="Request an engagement",
                href="/engagement_request",
            ),
            GuideLink(
                label="View live engagements",
                href="/pentesting/engagement",
            ),
        ),
    ),
)