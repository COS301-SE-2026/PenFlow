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

import { capitalize, cn } from "@/lib/utils";
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

const DEFAULT_WORKER_META: WorkerMeta = { label: "Unknown worker", icon: Info};

const WORKER_STATUS_CLASS_NAME: Record<string, string> = {
    completed: "border-brand-success bg-brand-success/10 text-brand-success",
    failed: "border-brand-alert bg-brand-alert/10 text-brand-alert",
    partial: "border-brand-yellow bg-brand-yellow/10 text-brand-yellow",
    running: "border-brand-cyan bg-brand-cyan/10 text-brand-cyan",
    pending: "border-muted-foreground/30 bg-muted/40 text-muted-foreground",
    skipped: "border-muted-foreground/30 bg-muted/40 text-muted-foreground",
};

const WORKER_DOT_CLASS_NAME: Record<string, string> = {
    completed: "bg-brand-success",
    failed: "bg-brand-alert",
    partial: "bg-brand-yellow",
    running: "bg-brand-cyan animate-pulse",
    pending: "bg-muted-foreground/40",
    skipped: "bg-muted-foreground/40",
};

const WORKER_STATUS_LABEL: Record<string, string> = {
    completed: "Successful",
    failed: "Failed",
    partial: "Partial",
    running: "Running",
    pending: "Pending",
    skipped: "Skipped",
};

function getWorkersMeta(sourceName: string): WorkerMeta {
    return WORKER_META[sourceName] ?? DEFAULT_WORKER_META;
}

export default function WorkerStatusGrid({ sources }: { sources: ScanSourceStatus[] }) {
    return (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {sources.map((source) => {
                const meta = getWorkersMeta(source.source_name);
                const Icon = meta.icon;
                const statusClassName = WORKER_STATUS_CLASS_NAME[source.status] ?? WORKER_STATUS_CLASS_NAME.pending;
                const statusLabel = WORKER_STATUS_LABEL[source.status] ?? capitalize(source.status);

                return (
                    <div
                        key={source.source_name}
                        className={cn("flex flex-col gap-2 rounded-lg border p-3.5", statusClassName)}
                    >
                        <div className="flex items-center gap-2">
                            <Icon className="size-4 shrink-0" />
                            <span className="min-w-0 flex-1 truncate text-sm font-medium text-foreground">{meta.label}</span>
                        </div>

                        <div className="flex items-center gap-1.5 text-xs uppercase tracking-wide">
                            <span className={cn("size-1.5 rounded-full", WORKER_DOT_CLASS_NAME[source.status] ?? WORKER_DOT_CLASS_NAME.pending)} />
                            {statusLabel}
                        </div>

                        {source.error_message && (
                            <p className="line-clamp-2 text-xs text-muted-foreground">{source.error_message}</p>
                        )}
                    </div>
                );
            })}
        </div>
    );
}