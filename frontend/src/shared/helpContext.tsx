import type {ReactNode} from "react";
export interface HelpTopic {
    id: string;
    title: string;
    body: ReactNode;
}

const domainsHelp: HelpTopic[] = [
    {
        id: "verify-domain",
        title: "How to verify domain ownership",
        body: (
            <>
                <p>Domain ownershup is proven with a DNS TXT record:</p>
                <ol>
                    <li>Open the domain&apos;s detail panel and copy the verification token shown there.</li>
                    <li>In your DNS provider, add a new TXT record at the root of your domain with that token as the value.</li>
                    <li>Save the record and give it time to propagate.</li>
                    <li>Come back and click Verify to check.</li>
                </ol>            
            </>
        ),
    },
    {
        id: "verification-failed",
        title: "Why verification failed",
        body: (
            <>
                <p>A failed check comes back with one of three reasons:</p>
                <ul>
                    <li><strong>No TXT record found</strong>Unable to find and TXT record at your domain&apos;s root. Double-check it was saved and added to the root domain, not a subdomain.</li>
                    <li><strong>Record found, but does not match</strong>a TXT record exists but its value does not match the token generated.</li>
                    <li><strong>Lookup failed</strong>Unable to reach domain DNS servers, try again later.</li>
                </ul>            
            </>
        ),
    },
    {
        id: "verification-time",
        title: "How long verification takes",
        body: (
                <p>DNS changes are not instant - It can take anywhere from a few minutes up to 24 hours, depending on the domain provider
                    and the record TTL. It is normal for a verification to fail immediately after adding a domain.
                </p>
                
        ),
    },
    {
        id: "status-badges",
        title: "What do the status badges mean?",
        body: (
                <ul>
                    <li><strong>Pending</strong> - the domain has been added but not verified yet.</li>
                    <li><strong>Verified</strong>- ownership has been confirmed via the TXT record.</li>
                    <li><strong>Failed</strong>- last verification attempt unsuccesful.</li>
                    <li><strong>Expired</strong>- verification is considered stale and ownership should be reconfirmed.</li>
                </ul>  
        ),
    },
];

const homeHelp: HelpTopic[] =[
    {
        id: "phase-1",
        title: "Phase 1 - Discover",
        body: (
                <p>
                    Passive OSINT reconnaissance. PenFlow pulls information about your target
                    from public sources - Shodan, HaveIbeenPwned, URLScan.io, crt.sh, WHOIS - 
                    whithout ever directly interacting with it. No domain verification required 
                    for phase 1.
                </p>
                
        ),
    },
    {
        id: "phase-2",
        title: "Phase 2 - Analyse",
        body: (
                <p>
                    An authorised, active scan of the external perimeter of your domain. - Open ports, service
                    and TLS configuration, and known CVEs - run in an isolated scan with severity scoring.
                    Due to the scan interacting directly with the target, domain verification is required.
                </p>
        ),
    },
    {
        id: "phase-3",
        title: "Phase 3 - React",
        body: (
                <p>
                    A managed-pentest pipeline. A professional pentester reviews and submits their findings about 
                    your domain while you are able to monitor them through an online portal.
                </p>
        ),
    },
];

const scanHomeHelp: HelpTopic[] =[
    {
        id: "active-scan",
        title: "Active scan",
        body: (
                <p>
                    An active scan directly interacts with the external perimeter of your domain. This includes: 
                    port scanning, TLS handshake, service fingerprinting, and CVE correlation - so it can only run
                     against a domain that is already verified.
                </p>
                
        ),
    },
    {
        id: "passive-scan",
        title: "Passive scan",
        body: (
                <p>
                    A passive scan only queries public, 3rd party sources about a domain - DNS records,
                    certificate transparency logs, Shodan, data breaches. The scan is fully passive and 
                    never touches the domain directly. Any domain can be passively scanned.
                </p>
        ),
    },
];

const scanProgressHelp: HelpTopic[] =[
    {
        id: "worker-detail",
        title: "What is a worker?",
        body: (
                <p>
                    Click on any worker tile in teh grid to see what each worker does.
                </p>
                
        ),
    },
    {
        id: "why-slow",
        title: "Scan is very slow",
        body: (
                <p>
                    Each step of a scan runs as its own worker task. Depending on earlier steps finshing first. If a worker hits 
                    an error such as a rate limit or timeout it will automatically retry up to 5 times before giving up. This can 
                    lead to scans sometimes taking longer than usual.
                </p>
        ),
    },
];

const scanResultsHelp: HelpTopic[] =[
    {
        id: "risk-score",
        title: "Risk score",
        body: (
                <p>
                    Summarises how risky the findings of the scan are. Thy consider how severe and critical each finding is.
                </p>
                
        ),
    },
    {
        id: "findings",
        title: "Findings",
        body: (
                <p>
                    Each finding is a specific issue uncovered during the scan eg: a missing security header or an outdated TLS config.
                    Each finding has a severity level, CVSS score and remediation recommendation.
                </p>
        ),
    },
    {
        id: "assets",
        title: "Assets",
        body: (
                <p>
                    Everything the scan discovered about your target: open ports, resolved IP addresses etc.
                    Each asset can have one or more findings tied to it.
                </p>
        ),
    },
    {
        id: "services",
        title: "Services",
        body: (
                <p>
                    The open ports and running services detected on your target, including the product,
                    version and state.
                </p>
        ),
    },
    {
        id: "activity",
        title: "Activity",
        body: (
                <p>
                    A log of every worker that ran as part of this scan and its current status.
                </p>
        ),
    },
];

const helpContentByRoute: Record<string, HelpTopic[]> = {
    "/": homeHelp,
    "/domains": domainsHelp,
    "/phase2_scan": scanHomeHelp,
    "/phase2_scan/progress": scanProgressHelp,
    "/phase2_scan/results": scanResultsHelp,
};

export function getHelpTopics(pathname: string): HelpTopic[] {
    const matches = Object.keys(helpContentByRoute).filter(
        (route) => pathname === route || pathname.startsWith(`${route}/`)
    );
    if (matches.length === 0) return [];
    const mostSpecific = matches.reduce(
        (longest, route) => (route.length > longest.length ? route: longest),
        matches[0]
    );
    return helpContentByRoute[mostSpecific];
}