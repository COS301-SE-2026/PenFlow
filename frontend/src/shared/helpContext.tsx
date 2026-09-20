import type { ReactNode } from "react"; 
import type { LucideIcon } from "lucide-react";
import {
    Activity,
    AlertTriangle,
    CalendarClock,
    CheckCircle2,
    ClipboardList,
    Clock3,
    Cog,
    Download,
    Eye,
    FileWarning,
    Gauge,
    History,
    ListChecks,
    Network,
    Pause,
    Radar,
    Search,
    Server,
    ShieldAlert,
    Tag,
    Users,
} from "lucide-react";

import { HelpList, HelpSteps } from "./components/HelpBits";

export type HelpAccent = "info" | "tip" | "warning";
export interface HelpTopic {
    id: string;
    title: string;
    icon?: LucideIcon;
    accent?: HelpAccent;
    body: ReactNode;
}

const domainsHelp: HelpTopic[] = [
{
    id: "verify-domain",
    title: "How to verify domain ownership",
    icon: ListChecks,
    body: (
        <>
            <p>Domain ownership is proven with a DNS TXT record:</p>
            <HelpSteps
                items={[
                    <>Open the domain&apos;s detail panel and copy the verification token shown there.</>,
                    <>In your DNS provider, add a new TXT record at the root of your domain with that token as the value.</>,
                    <>Save the record and give it time to propagate.</>,
                    <>Come back and click Verify to check.</>,
                ]}
            />
        </>
    ),
},
{
    id: "verification-failed",
    title: "Why verification failed",
    icon: AlertTriangle,
    accent: "warning",
    body: (
        <>
            <p>A failed check comes back with one of three reasons:</p>
            <HelpList
                tone="warning" 
                items={[
                    <><strong>No TXT record found</strong> - unable to find a TXT record at your domain&apos;s root. Double-check it was saved and added to the root domain, not a subdomain.</>, 
                    <><strong>Record found, but does not match</strong> - a TXT record exists but its value does not match the token generated.</>, 
                    <><strong>Lookup failed</strong> - unable to reach domain DNS servers, try again later.</>,
                ]}
            />
        </>
    ),
},
{
    id: "verification-time",
    title: "How long verification takes",
    icon: Clock3,
    accent: "tip",
    body: (
        <p>DNS changes are not instant - It can take anywhere from a few minutes up to 24 hours, depending on the domain provider and the record TTL. It is normal for a verification to fail immediately after adding a domain.
        </p>
    ),
},
{
    id: "status-badges",
    title: "What do the status badges mean?",
    icon: Tag,
    body: (
        <HelpList
            items={[
                <><strong>Pending</strong> - the domain has been added but not verified yet.</>,
                <><strong>Verified</strong> - ownership has been confirmed via the TXT record.</>,
                <><strong>Failed</strong> - last verification attempt unsuccesful.</>,
                <><strong>Expired</strong> - verification is considered stale and ownership should be reconfirmed.</>,
            ]}
        />
    ),
},
];

const homeHelp: HelpTopic[] = [
    {
        id: "phase-1",
        title: "Phase 1 - Discover",
        icon: Radar,
        body: (
            <p>Passive OSINT reconnaissance. PenFlow pulls information about your target from public sources Shodan, HaveIbeenPwned, URLScan.io, crt.sh, WHOIS whithout ever directly interacting with it. No domain verification required for phase 1.
            </p>
        ),
    },
    {
        id: "phase-2",
        title: "Phase 2 Analyse",
        icon: ShieldAlert,
        body: (
            <p>An authorised, active scan of the external perimeter of your domain. - Open ports, service and TLS configuration, and known CVEs - run in an isolated scan with severity scoring. Due to the scan interacting directly with the target, domain verification is required.</p>
        ),
    },
    {
        id: "phase-3",
        title: "Phase 3",
        icon: Users,
        body: (
            <p>A managed-pentest pipeline. A professional pentester reviews and submits their findings about your domain while you are able to monitor them through an online portal.</p>
        ),
    },
];

const scanHomeHelp: HelpTopic[] = [
    {
        id: "active-scan",
        title: "Active scan",
        icon: ShieldAlert,
        body: (
            <p>
                An active scan directly interacts with the external perimeter of your domain. This includes: port scanning, TLS handshake, service fingerprinting, and CVE correlation against a domain that is already verified.
            </p>
        ),
    },
    {
        id: "passive-scan",
        title: "Passive scan",
        icon: Radar,
        body: (
            <p>
                A passive scan only queries public, 3rd party sour ources about a domain - DNS records, certificate transparency logs, Shodan, data breaches. The scan is fully passive and never touches the domain directly. Any domain can be passively scanned.
            </p>
        ),
    },
];

const scanProgressHelp: HelpTopic[] = [
    {
        id: "worker-detail",
        title: "What is a worker?",
        icon: Cog,
        body: (
            <p>
                Each step of a scan runs as its own worker task, and some steps depend on earlier steps finishing first. If a
                worker hits an error such as a rate limit or timeout, it will automatically retry up to 5 times before giving
                up. This can sometimes make scans take longer than usual.
            </p>
        ),
    },
];

const scanResultsHelp: HelpTopic[] = [
    {
        id: "risk-score",
        title: "Risk score",
        icon: Gauge,
        body: (
            <p>
                Summarises how risky the findings of the scan are, taking into account the severity and criticality of each finding.
            </p>
        ),
    },
    {
        id: "findings",
        title: "Findings",
        icon: FileWarning,
        body: (
            <p>
                Each finding is a specific issue uncovered during the scan, e.g. a missing security header or an outdated TLS configuration.
                Each finding has a severity level, a CVSS score and a remediation recommendation.
            </p>
        ),
    },
    {
        id: "assets",
        title: "Assets",
        icon: Server,
        body: (
            <p>
                Everything the scan discovered about your target, such as open ports and resolved IP addresses.
                Each asset can have one or more findings tied to it.
            </p>
        ),
    },
    {
        id: "services",
        title: "Services",
        icon: Network,
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
        icon: Activity,
        body: (
            <p>
                A log of every worker that ran as part of this scan, along with its current status.
            </p>
        ),
    },
];

const scheduledScansHelp: HelpTopic[] = [
    {
        id: "what-is-a-schedule",
        title: "What is a scheduled scan?",
        icon: CalendarClock,
        body: (
            <p>
                A recurring active vulnerability scan against one of your verified domains. Once created,
                PenFlow automatically launches a scan for you on the chosen day and time - no need to
                start it manually.
            </p>
        ),
    },
    {
        id: "creating-a-schedule",
        title: "Creating a schedule",
        icon: ListChecks,
        body: (
            <>
                <p>Click &quot;New schedule&quot; and set:</p>
                <HelpList
                    items={[
                        <><strong>Verified domain</strong> - only verified domains can be scheduled.</>,
                        <><strong>Frequency</strong> - weekly (pick a day of the week) or monthly (pick a day of the month, 1-28).</>,
                        <><strong>Run time and timezone</strong> - when the scan should kick off.</>,
                    ]}
                />
                <p>A domain can only have one schedule per scan type - the target can&apos;t be changed after creation, so create a new schedule instead.</p>
            </>
        ),
    },
    {
        id: "pause-resume-delete",
        title: "Pause, resume, and delete",
        icon: Pause,
        accent: "tip",
        body: (
            <p>
                Pausing a schedule keeps its configuration but stops it from creating new scans - use
                Resume to pick it back up. Deleting a schedule removes it permanently; you&apos;ll be
                asked to confirm first.
            </p>
        ),
    },
    {
        id: "next-last-run",
        title: "Next run and last run",
        icon: Clock3,
        body: (
            <p>
                &quot;Next run&quot; shows when the schedule will next fire (only shown while active).
                &quot;Last run&quot; shows when it last actually created a scan, or &quot;Never&quot; if
                it hasn&apos;t run yet.
            </p>
        ),
    },
];

const scanHistoryHelp: HelpTopic[] = [
    {
        id: "history-overview",
        title: "What is shown here?",
        icon: History,
        body: (
            <p>
                Every scan you&apos;ve ever run, newest first - both passive reconnaissance and active
                vulnerability scans, whether triggered manually or by a schedule.
            </p>
        ),
    },
    {
        id: "history-status",
        title: "Scan status",
        icon: ListChecks,
        body: (
            <HelpList
                items={[
                    <><strong>Queued</strong> - waiting for a worker to pick it up.</>,
                    <><strong>Running</strong> - currently in progress.</>,
                    <><strong>Completed</strong> - finished successfully.</>,
                    <><strong>Partial</strong> - finished, but one or more steps failed.</>,
                    <><strong>Failed</strong> - the scan could not complete.</>,
                ]}
            />
        ),
    },
    {
        id: "history-actions",
        title: "Viewing and sharing a report",
        icon: Download,
        accent: "tip",
        body: (
            <p>
                Click a row (or &quot;View Results&quot;) to open the full findings for that scan.
                Use the download icon to save the PDF report, or open the row&apos;s menu to email
                the report to an address of your choice.
            </p>
        ),
    },
];