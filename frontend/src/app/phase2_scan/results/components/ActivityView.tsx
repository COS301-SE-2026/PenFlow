"use client"

import { useEffect, useState } from "react";

import { fetchScanStatus, type RealTimeScanStatus } from "@/lib/scanService";
import WorkerStatusGrid from "./WorkerStatusGrid";

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
}