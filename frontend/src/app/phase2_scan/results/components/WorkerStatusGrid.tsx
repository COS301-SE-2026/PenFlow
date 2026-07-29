import {
    Bug,
    Crosshair,
    FileSearch,
    Fingerprint,
    Globe,
    Info,
    Lock,
    Network,
    ShieldAlert,
    ShieldCheck,
    type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { ScanSourceStatus } from "@/lib/scanService";

interface WorkerMeta {
    label: string;
    icon: LucideIcon;
}

const WORKER_META: Record<string, WorkerMeta> = {
    dns: { label: "DNS", icon: Network },
    "crt.sh": { label: "crt.sh", icon: FileSearch },
    urlscan: { label: "URLScan", icon: Globe },
    wappalyzer: { label: "Wappalyzer", icon: Fingerprint },
    shodan: { label: "Shodan", icon: Fingerprint },
    hibp: { label: "HaveIBeenPwned", icon: ShieldAlert },
    target_resolution: { label: "Resolving Target", icon: Globe },
    nmap: { label: "Discovering Ports", icon: Crosshair },
    http_security: { label: "Checking HTTP", icon: ShieldCheck },
    tls: { label: "Inspecting TLS", icon: Lock },
    fingerprint: { label: "Detecting Tech", icon: Fingerprint },
    cve: { label: "Matching CVEs", icon: Bug },
};