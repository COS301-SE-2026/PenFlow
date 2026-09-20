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
