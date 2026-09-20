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
        
    }
];