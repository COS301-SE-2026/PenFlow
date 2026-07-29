"use client"

import { useEffect, useState } from "react";

import { fetchScanStatus, type RealTimeScanStatus } from "@/lib/scanService";
import WorkerStatusGrid from "./WorkerStatusGrid";
import { INSPECT_MAX_BYTES } from "buffer";

const scanTypeLabel: Record<string, string> = {
    active_vulnerability: "Active Vulnerability Scan",
    passive_ctem: "Passive Reconnaissance",
};

function formatElapsed(startIso: string): string {
    const ms = Date.now() - new Date(startIso).getTime();
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

const TERMINAL_SOURCE_STATUSES = new Set(["completed", "failed", "partial", "skipped"]);

export default function ActivityView({ scanId }: { scanId: string }) {
    const [scan, setScan] = useState<RealTimeScanStatus | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        fetchScanStatus(scanId)
            .then(setScan)
            .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load scan activity"))
            .finally (() => setLoading(false));
    }, [scanId]);

    if (error) {
        return (
            <section className="min-w-0" data-scan-id={scanId}>
                <p className="text-sm text-muted-foreground">{error}</p>
            </section>
        );
    }

    if (loading || !scan) {
        return (
            <section className="min-w-0" data-scan-id={scanId}>
                <p className="text-sm text-muted-foreground">Loading scan activity...</p>
            </section>
        );
    }

    const visibleSources = scan.sources.filter((s) => s.source_name !== "hunter.io");
    const completedCount = visibleSources.filter((s) => TERMINAL_SOURCE_STATUSES.has(s.status)).length;

    const details: { label: string; value: string }[] = [
        { label: "Domain", value: scan.domain },
        { label: "Scan Type", value: scanTypeLabel[scan.scan_type] ?? scan.scan_type },
        { label: "Status", value: scan.status },
        { label: "Elapsed Time", value: formatElapsed(scan.created_at) },
        { label: "Sources Completed", value: `${completedCount} / ${visibleSources.length}`},
    ];

    return (
        <section className="min-w-0" data-scan-id={scanId}>
            <div className="mb-5 rounded-[10px] border border-brand-panel-border bg-[#ob1625] p-[18px]">
                <div className="flex flex-wrap items-center gap-x-8 gap-y-4">
                    {details.map((item, index) => (
                        <div key={item.label} className="flex items-center gap-8">
                            <div className="flex flex-col gap-1">
                                <span className="text-xs uppercase tracking-wide text-muted-foreground">{item.label}</span>
                                <span className="text-base font-medium whitespace-nowrap text-foreground capitalize">
                                    {item.value}
                                </span>
                            </div>
                            {index < details.length - 1 && (
                                <span className="hidden h-8 w-px bg-brand-panel-border sm:block" />
                            )}
                        </div>
                    ))}
                </div>
            </div>

            <div className="rounded-[10px] border border-brand-panel-border bg-[#0b1625] p-[18px]">
                <h2 className="mb-4 text-sm font-bold uppercase tracking-[0.15em] text-foreground/90">Worker Activity</h2>
                <WorkerStatusGrid sources={visibleSources} />
            </div>
        </section>
    );
}