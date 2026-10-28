"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bug, ChevronDown, ChevronRight, Globe, LineChart, Loader2, Network, Radar } from "lucide-react";

import { cn, capitalize } from "@/lib/utils";
import {
    fetchScanMetrics,
    type RiskHistoryItem, type ScanHistoryItem, type ScanMetrics,
} from "@/lib/scanService";
import { formatDateWithYear } from "@/lib/engagementFormat";
import { RiskGauge, RiskHistoryChart } from "./results/components/ScanResultsOverview";
import { FINDINGS_COLORS, PANEL_CLASS_NAME, SummaryCard } from "./results/components/SummaryCard";
import { TYPE_COLOR, typeKey, typeLabel } from "./results/components/assetTypes";

const FINISHED_STATUSES = new Set(["completed", "partial"]);
const RUNNING_STATUSES = new Set(["queued", "running"]);
const SEVERITIES = ["critical", "high", "medium", "low", "info"] as const;
const SERVICE_COLORS = ["#a855f7", "#c084fc", "#7c3aed", "#d8b4fe"];

const scanTypeLabel: Record<string, string> = {
    active_vulnerability: "Active",
    passive_ctem: "Passive",
};

export type ScanView = "active" | "passive";
const SCAN_TYPE_OF: Record<ScanView, string> = { active: "active_vulnerability", passive: "passive_ctem" };

type LastScanData = { metrics: ScanMetrics; previous: ScanMetrics | null };

const cache = new Map<string, LastScanData>();

function riskColor(score: number) {
    return score >= 70 ? "#ef4444" : score >= 40 ? "#facc15" : "#4ade80";
}

function entriesOf(map: Record<string, number>, label: (key: string) => string) {
    return Object.entries(map).filter(([key]) => key !== "total").map(([key, value]) => ({ key, label: label(key), value }));
}

function riskLevelText(level: string): string {
    const words = level.replace(/_/g, " ").toLowerCase().trim();
    const text = words.endsWith("risk") ? words : `${words} risk`;
    return capitalize(text);
}

function riskScoreOf(scan: ScanHistoryItem): number {
    return Math.min(100, scan.critical_count * 25 + scan.high_count * 15 + scan.medium_count * 5 + scan.low_count);
}

function deltaOf(current: number | undefined, previous: number | undefined, upIsBad = false) {
    if (current === undefined || previous === undefined) return null;
    return { value: current - previous, upIsBad };
}

export default function DomainLastScanPanel({ domain, scans, view, onViewChange, action }: {
    domain: string;
    scans: ScanHistoryItem[];
    view: ScanView;
    onViewChange: (view: ScanView) => void;
    action?: React.ReactNode;
}) {
    const key = domain.toLowerCase();
    const setView = onViewChange;
    const forDomain = scans.filter((scan) => scan.domain.toLowerCase() === key);
    const finishedAll = forDomain.filter((scan) => FINISHED_STATUSES.has(scan.status));
    const finished = finishedAll
        .filter((scan) => scan.scan_type === SCAN_TYPE_OF[view])
        .sort((a, b) => b.created_at.localeCompare(a.created_at));
    const otherView: ScanView = view === "active" ? "passive" : "active";
    const hasOther = finishedAll.some((scan) => scan.scan_type === SCAN_TYPE_OF[otherView]);
    const chartScans = forDomain
        .filter((scan) => (FINISHED_STATUSES.has(scan.status) || scan.status === "failed") && scan.scan_type === SCAN_TYPE_OF[view])
        .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
    const history: RiskHistoryItem[] = chartScans.map((scan) => ({
        scan_id: scan.id,
        status: scan.status,
        date: new Date(scan.created_at).toLocaleDateString("en-US", { month: "short", day: "2-digit" }),
        risk_score: riskScoreOf(scan),
        total_findings: scan.total_findings,
    }));

    const [selection, setSelection] = useState<{ view: ScanView; id: string } | null>(null);
    const newest = finished[0] ?? null;
    const selected = selection && selection.view === view ? chartScans.find((scan) => scan.id === selection.id) ?? null : null;
    const latest = selected ?? newest;
    const showingLatest = !selected || selected.id === newest?.id;
    const previousScan = latest
        ? finished.find((scan) => new Date(scan.created_at).getTime() < new Date(latest.created_at).getTime()) ?? null
        : null;
    const running = forDomain.find((scan) => RUNNING_STATUSES.has(scan.status)) ?? null;

    const cacheKey = latest ? `${latest.id}|${previousScan?.id ?? ""}` : "";
    const [data, setData] = useState<LastScanData | null>(cacheKey ? cache.get(cacheKey) ?? null : null);
    const [error, setError] = useState<string | null>(null);
    const [open, setOpen] = useState(false);

    useEffect(() => {
        if (!latest) return;
        const cached = cache.get(cacheKey);
        if (cached) {
            setData(cached);
            return;
        }
        let cancelled = false;
        setData(null);
        setError(null);
        Promise.all([
            fetchScanMetrics(latest.id),
            previousScan ? fetchScanMetrics(previousScan.id).catch(() => null) : Promise.resolve(null),
        ])
            .then(([metrics, previous]) => {
                const loaded = { metrics, previous };
                cache.set(cacheKey, loaded);
                if (!cancelled) setData(loaded);
            })
            .catch((err: unknown) => {
                if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load the last scan");
            });
        return () => { cancelled = true; };
    }, [cacheKey]); // eslint-disable-line react-hooks/exhaustive-deps

    const viewSwitch = (
        <div role="tablist" aria-label="Scan type" className="inline-flex rounded-lg border border-brand-panel-border bg-brand-panel-deep p-0.5">
            {(["active", "passive"] as const).map((option) => (
                <button
                    key={option}
                    type="button"
                    role="tab"
                    aria-selected={view === option}
                    onClick={() => setView(option)}
                    className={cn(
                        "rounded-md px-2.5 py-1 text-xs font-medium capitalize transition-colors",
                        view === option
                            ? option === "active" ? "bg-brand-cyan/15 text-brand-cyan" : "bg-[#a78bfa]/15 text-[#a78bfa]"
                            : "text-muted-foreground hover:text-foreground"
                    )}
                >
                    {option}
                </button>
            ))}
        </div>
    );

    const scanLabel = latest
        ? `${formatDateWithYear(latest.created_at)} · ${scanTypeLabel[latest.scan_type] ?? capitalize(latest.scan_type)}`
        : "";

    const lastScanHeading = latest && (
        <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
                <span className="flex size-7 items-center justify-center rounded-lg bg-brand-cyan/10 text-brand-cyan">
                    <LineChart className="size-4" />
                </span>
                <h3 className="m-0 text-[13px] font-semibold text-foreground uppercase [font-family:inherit]!">
                    {showingLatest ? "Last scan" : "Selected scan"} <span className="font-normal text-muted-foreground normal-case">· {scanLabel}</span>
                </h3>
                {!showingLatest && (
                    <button type="button" onClick={() => setSelection(null)} className="text-xs font-medium text-brand-cyan hover:underline">
                        Show latest
                    </button>
                )}
            </div>
            <Link href={`/phase2_scan/results/${latest.id}`} className="inline-flex items-center gap-1 text-sm font-medium text-brand-cyan no-underline hover:underline">
                View full results <ChevronRight className="size-4" />
            </Link>
        </div>
    );

    let body: React.ReactNode;
    if (finishedAll.length === 0) {
        body = (
            <div className="flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-brand-panel-border p-4">
                <Radar className="size-5 shrink-0 text-muted-foreground" />
                <p className="flex-1 text-sm text-muted-foreground">No scans yet. Start one to see this domain&apos;s risk and trend.</p>
                {action}
            </div>
        );
    } else if (!latest) {
        body = (
            <div className="flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-brand-panel-border p-4">
                <Radar className="size-5 shrink-0 text-muted-foreground" />
                <p className="flex-1 text-sm text-muted-foreground">No {view} scans of this domain yet.</p>
                {viewSwitch}
                {hasOther && (
                    <button type="button" onClick={() => setView(otherView)} className="text-sm font-medium text-brand-cyan hover:underline">
                        View {otherView} history
                    </button>
                )}
                {action}
            </div>
        );
    } else if (error) {
        body = (
            <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-brand-alert">{error}</p>
                {action}
            </div>
        );
    } else if (!data) {
        body = (
            <div className="flex flex-col gap-3">
                {action && <div className="flex justify-end">{action}</div>}
                <div className="h-[260px] animate-pulse rounded-[10px] border border-brand-panel-border bg-white/[0.02]" />
                <div className="grid grid-cols-[1.2fr_1fr_1fr_1fr] gap-3 max-[1500px]:grid-cols-2 max-sm:grid-cols-1">
                    {[0, 1, 2, 3].map((i) => <div key={i} className="h-[170px] animate-pulse rounded-[10px] border border-brand-panel-border bg-white/[0.02]" />)}
                </div>
            </div>
        );
    } else {
        const { metrics, previous } = data;
        const urgent = metrics.findings.critical + metrics.findings.high;
        const assetItems = entriesOf(metrics.assets, typeLabel);
        const serviceItems = entriesOf(metrics.services, (k) => k.toUpperCase());
        const firstDate = history[0]?.date;
        body = (
            <div className="flex flex-col gap-3">
                <article className={cn(PANEL_CLASS_NAME, "flex flex-col border")}>
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-[13px] text-foreground uppercase [font-family:inherit]!">Risk Over Time</h3>
                            <span className="text-xs text-muted-foreground">
                                {history.length} {view} scan{history.length === 1 ? "" : "s"}{firstDate ? ` since ${firstDate}` : ""}
                            </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            {viewSwitch}
                            {action}
                        </div>
                    </div>
                    {history.length < 2 ? (
                        <p className="m-auto py-10 text-center text-sm text-muted-foreground">Run another {view} scan to see a trend.</p>
                    ) : (
                        <RiskHistoryChart history={history} currentScanId={latest?.id} onSelect={(id) => setSelection({ view, id })} />
                    )}
                </article>

                <article className={cn(PANEL_CLASS_NAME, "flex flex-col gap-4 border")}>
                {lastScanHeading}

                <div className="grid grid-cols-[1.2fr_1fr_1fr_1fr] items-stretch gap-4 max-[1500px]:grid-cols-2 max-sm:grid-cols-1 min-[1500px]:gap-0 min-[1500px]:[&>*+*]:border-l min-[1500px]:[&>*+*]:border-brand-panel-border min-[1500px]:[&>*+*]:pl-5 min-[1500px]:[&>*:not(:last-child)]:pr-5">
                    <div className="flex flex-col justify-center">
                        <span className="text-[11px] font-semibold text-[#cbd5e1] uppercase">Risk score</span>
                        <RiskGauge score={metrics.risk_score} />
                        <p className="m-0 -mt-1 text-center">
                            <strong className="text-[28px] leading-none" style={{ color: riskColor(metrics.risk_score) }}>{metrics.risk_score}</strong>
                            <span className="text-xs text-muted-foreground">/100</span>
                        </p>
                        <p className="m-0 mt-1 text-center text-[11px] font-semibold uppercase" style={{ color: riskColor(metrics.risk_score) }}>
                            {riskLevelText(metrics.risk_level)}
                        </p>
                        {previous && (
                            <p className={cn("m-0 mt-1 text-center text-[11px] font-semibold",
                                metrics.risk_score > previous.risk_score ? "text-brand-alert" : metrics.risk_score < previous.risk_score ? "text-brand-success" : "text-[#94a3b8]")}>
                                {metrics.risk_score === previous.risk_score
                                    ? "No change"
                                    : `${metrics.risk_score > previous.risk_score ? "▲" : "▼"} ${Math.abs(metrics.risk_score - previous.risk_score)}`}
                                <span className="font-normal text-[#64748b]"> since previous scan</span>
                            </p>
                        )}
                    </div>
                    <SummaryCard
                        layout="compact"
                        className="border-0 bg-transparent p-0 shadow-none max-[650px]:p-0"
                        title="Findings"
                        icon={Bug}
                        accentClassName="bg-brand-alert/10 text-brand-alert"
                        value={metrics.findings.total}
                        items={SEVERITIES.map((sev) => ({ label: capitalize(sev), value: metrics.findings[sev] }))}
                        colors={SEVERITIES.map((sev) => FINDINGS_COLORS[sev])}
                        subtitle={urgent > 0 ? <span className="text-brand-alert">{urgent} critical/high</span> : "No critical or high"}
                        delta={deltaOf(metrics.findings.total, previous?.findings.total, true)}
                    />
                    <SummaryCard
                        layout="compact"
                        className="border-0 bg-transparent p-0 shadow-none max-[650px]:p-0"
                        title="Assets"
                        icon={Globe}
                        accentClassName="bg-brand-cyan/10 text-brand-cyan"
                        value={metrics.assets.total ?? 0}
                        items={assetItems}
                        colors={assetItems.map((item) => TYPE_COLOR[typeKey(item.key)] ?? "#c084fc")}
                        delta={deltaOf(metrics.assets.total, previous?.assets.total)}
                    />
                    <SummaryCard
                        layout="compact"
                        className="border-0 bg-transparent p-0 shadow-none max-[650px]:p-0"
                        title="Services"
                        icon={Network}
                        accentClassName="bg-[#a855f7]/10 text-[#c084fc]"
                        value={metrics.services.total ?? 0}
                        items={serviceItems}
                        colors={serviceItems.map((_, i) => SERVICE_COLORS[i % SERVICE_COLORS.length])}
                        delta={deltaOf(metrics.services.total, previous?.services.total)}
                    />
                </div>
                </article>
            </div>
        );
    }

    return (
        <section className="flex min-w-0 flex-col gap-3 animate-in fade-in slide-in-from-right-2 duration-300" aria-label={`Last scan of ${domain}`}>
            <button
                type="button"
                onClick={() => setOpen((prev) => !prev)}
                aria-expanded={open}
                className="hidden items-center justify-between gap-2 rounded-lg border border-brand-panel-border px-3 py-2.5 text-left max-sm:flex"
            >
                <span className="text-[13px] font-semibold text-foreground uppercase">
                    Last scan {scanLabel && <span className="font-normal text-muted-foreground normal-case">· {scanLabel}</span>}
                </span>
                <ChevronDown aria-hidden="true" className={cn("size-4 text-muted-foreground transition-transform", open && "rotate-180")} />
            </button>
            <div className={cn("flex flex-col gap-3", !open && "max-sm:hidden")}>
                {running && (
                    <Link
                        href={`/phase2_scan/progress?scan_id=${running.id}`}
                        className="flex items-center gap-3 rounded-lg border border-brand-cyan/40 bg-brand-cyan/[0.06] px-3 py-2.5 text-sm no-underline"
                    >
                        <Loader2 className="size-4 shrink-0 animate-spin text-brand-cyan" />
                        <span className="flex-1 text-foreground">
                            Scan in progress · {running.progress}%
                            <span className="ml-2 text-xs text-muted-foreground">A scan of this domain is already running.</span>
                        </span>
                        <span className="inline-flex items-center gap-1 text-brand-cyan">View progress <ChevronRight className="size-4" /></span>
                    </Link>
                )}
                {body}
            </div>
        </section>
    );
}