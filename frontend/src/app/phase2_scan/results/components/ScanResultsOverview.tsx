"use client";
import {useCallback, useEffect, useMemo, useState} from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, Bug, ChevronDown, ChevronRight, Globe, Layers, Network, ShieldAlert, Target, type LucideIcon } from "lucide-react";
import { FindingDetails } from "./FindingsGrid";
import { AssetDetails, buildInsights } from "./AssetsGrid";
import { TYPE_COLOR, TypeBadge, isIpType, typeKey, typeLabel } from "./assetTypes";
import { FINDINGS_COLORS, PANEL_CLASS_NAME, SummaryCard } from "./SummaryCard";
import { capitalize, cn } from "@/lib/utils";
import{fetchScanMetrics, fetchScanFindings, fetchScanAssets,fetchScanRiskHistory, fetchScanGraph, fetchScanGraphCompare, fetchScanHistory, type GraphCompareResponse, type ScanGraphResponse,
    type ScanMetrics,
    type DashboardFindingItem,
    type DashboardAssetItem,
    type RiskHistoryItem,
    type ScanHistoryItem,
} from "@/lib/scanService";


const severityClassName: Record<string, string> = {
    critical: "border-[#991b1b] text-brand-alert bg-brand-alert/10",
    high: "border-brand-orange/70 text-brand-orange bg-brand-orange/10",
    medium: "border-brand-yellow/70 text-brand-yellow bg-brand-yellow/10",
    low: "border-[#1e40af] text-[#60a5fa] bg-[#1e40af]/10",
    info: "border-[#334155] text-[#94a3b8] bg-[#334155]/10",
};




function riskLevelLabel(level: string): string {
    return level.split("_").map((word) => capitalize(word.toLowerCase())).join(" ");
}

function riskLevelColorClass(level: string): string {
    const normalized = level.toUpperCase();
    if (normalized.startsWith("HIGH")) return "text-brand-alert";
    if (normalized.startsWith("MEDIUM")) return "text-brand-yellow";
    return "text-brand-success";
}

type ChartView = "active" | "passive";
const CHART_SCAN_TYPE: Record<ChartView, string> = { active: "active_vulnerability", passive: "passive_ctem" };

const PROBLEM_COLOR = "#f97316";

const RISK_ZONES = [
    { from: 0, to: 40, color: "#4ade80", label: "Low" },
    { from: 40, to: 70, color: "#facc15", label: "Medium" },
    { from: 70, to: 100, color: "#ef4444", label: "High" },
];

export function RiskGauge({score}: {score: number}) {
    const clamped = Math.max(0, Math.min(100, score));
    const point = (value: number, radius: number) => {
        const angle = Math.PI * (1 - value / 100);
        return [90 + radius * Math.cos(angle), 90 - radius * Math.sin(angle)];
    };
    const arc = (from: number, to: number) => {
        const [x1, y1] = point(from, 70);
        const [x2, y2] = point(to, 70);
        return `M ${x1} ${y1} A 70 70 0 0 1 ${x2} ${y2}`;
    };
    const [nx, ny] = point(clamped, 54);
    const active = RISK_ZONES.find((z) => clamped >= z.from && (clamped < z.to || z.to === 100)) ?? RISK_ZONES[0];
    return (
        <svg viewBox="0 0 180 100" className="mx-auto mt-1 block w-[180px]" role="img" aria-label={`Risk score ${clamped} out of 100`}>
            {RISK_ZONES.map((zone) => (
                <path key={zone.from} d={arc(zone.from + (zone.from ? 0.8 : 0), zone.to - (zone.to < 100 ? 0.8 : 0))}
                    fill="none" stroke={zone.color} strokeWidth={13} opacity={zone === active ? 1 : 0.3} />
            ))}
            <line x1={90} y1={90} x2={nx} y2={ny} stroke="#e5f3ff" strokeWidth={3} strokeLinecap="round" />
            <circle cx={90} cy={90} r={5} fill="#e5f3ff" />
        </svg>
    );
}


function zoneFor(score: number) {
    return RISK_ZONES.find((z) => score < z.to) ?? RISK_ZONES[RISK_ZONES.length - 1];
}

function RiskPointTooltip({history, index, x, y, currentScanId, selectMode = false}: {history: RiskHistoryItem[]; index: number; x: number; y: number; currentScanId?: string; selectMode?: boolean}) {
    const item = history[index];
    const zone = zoneFor(item.risk_score);
    const problem = item.status === "partial" || item.status === "failed";
    const change = index > 0 ? item.risk_score - history[index - 1].risk_score : null;
    const horizontal = x < 0.2 ? "translate-x-0" : x > 0.8 ? "-translate-x-full" : "-translate-x-1/2";
    const below = y < 0.4;

    return (
        <div className="pointer-events-none absolute inset-x-0 top-0 bottom-[22px] z-10">
            <div
                role="tooltip"
                className={cn(
                    "absolute w-max min-w-[150px] rounded-lg border border-brand-panel-border bg-[#0b1625]/95 px-3 py-2 text-xs shadow-lg shadow-black/40 backdrop-blur",
                    horizontal,
                    below ? "mt-3" : "-mt-3 -translate-y-full",
                )}
                style={{ left: `${x * 100}%`, top: `${y * 100}%` }}
            >
                <p className="text-[11px] text-muted-foreground">{item.date}</p>
                {problem && (
                    <p className="mt-1 flex items-center gap-1.5 font-semibold" style={{ color: PROBLEM_COLOR }}>
                        <AlertTriangle className="size-3.5" />
                        {item.status === "failed" ? "Failed scan" : "Partial scan"}
                    </p>
                )}
                <p className="mt-1 flex items-center gap-1.5 font-semibold text-foreground">
                    <span className="size-2 rounded-full" style={{ backgroundColor: zone.color }} />
                    Risk {item.risk_score}
                    <span className="font-medium" style={{ color: zone.color }}>· {zone.label}</span>
                </p>
                <p className="mt-1 flex items-center gap-2 text-muted-foreground">
                    <span>{item.total_findings} finding{item.total_findings === 1 ? "" : "s"}</span>
                    {change !== null && change !== 0 && (
                        <span className={cn("font-medium", change > 0 ? "text-[#ef4444]" : "text-[#4ade80]")}>
                            {change > 0 ? `▲ ${change}` : `▼ ${Math.abs(change)}`} vs prev
                        </span>
                    )}
                </p>
                {item.scan_id && (
                    <p className="mt-1.5 border-t border-brand-panel-border pt-1.5 text-[11px] text-muted-foreground">
                        {item.scan_id === currentScanId
                            ? (selectMode ? "Shown below" : "This scan")
                            : (selectMode ? "Click to show this scan below" : "Click to open this scan")}
                    </p>
                )}
            </div>
        </div>
    );
}

export function RiskHistoryChart({history, currentScanId, onSelect}: {history: RiskHistoryItem[]; currentScanId?: string; onSelect?: (scanId: string) => void}) {
    const [hovered, setHovered] = useState<number | null>(null);
    const router = useRouter();
    const openPoint = (index: number) => {
        const id = history[index]?.scan_id;
        if (!id || id === currentScanId) return;
        if (onSelect) onSelect(id);
        else router.push(`/phase2_scan/results/${id}`);
    };

    if (history.length < 2) {
        return <p className="mt-[15px] text-xs text-muted-foreground"> Not enough historical scans yet to chart a trend. </p>;
    }

    const width = 600;
    const height = 220;
    const step = width / (history.length -1);
    const points = history.map((item, index) => {
        const x = index * step;
        const y = height - (item.risk_score / 100) * height;
        return {x,y};
    });

    const linePoints = points.map((p) => `${p.x},${p.y}`).join(" ");
    const yFor = (score: number) => height - (score / 100) * height;

    return (
        <div className="flex h-[220px] gap-2.5">
            <div className="flex flex-col justify-between pb-[22px] text-[10px] text-muted-foreground">
                <span>100</span>
                <span>75</span>
                <span>50</span>
                <span>25</span>
                <span>0</span>
            </div>

            <div className="relative min-w-0 flex-1">
                <div 
                    className="absolute inset-x-0 top-0 bottom-[22px]"
                    style = {{
                        backgroundImage: "linear-gradient(to right, rgb(51 65 85 / 35%) 1px, transparent 1px), linear-gradient(to bottom, rgb(51 65 85 / 35%) 1px, transparent 1px)",
                        backgroundSize: "12.5% 25%",
                    }}
                />
                    <svg
                        viewBox={`0 0 ${width} ${height}`}
                        preserveAspectRatio="none"
                        aria-label = {`Risk score over the last ${history.length} scans`}
                        className="absolute inset-x-0 top-0 bottom-[22px] h-[calc(100%-22px)] w-full overflow-visible"
                    >
                        {RISK_ZONES.map((zone) => (
                            <rect key={zone.from} x={0} y={yFor(zone.to)} width={width} height={yFor(zone.from) - yFor(zone.to)} fill={zone.color} opacity={0.07} />
                        ))}
                        {[40, 70].map((threshold) => (
                            <line key={threshold} x1={0} x2={width} y1={yFor(threshold)} y2={yFor(threshold)}
                                stroke="#64748b" strokeDasharray="4 4" style={{ strokeWidth: 1, vectorEffect: "non-scaling-stroke" }} />
                        ))}
                        <polyline
                            points = {linePoints}
                            className="fill-none stroke-[#94a3b8]"
                            style = {{strokeWidth: 2, vectorEffect: "non-scaling-stroke"}}
                        />
                    </svg>
                    <div className="pointer-events-none absolute inset-x-0 top-0 bottom-[22px]">
                        {points.map((p, index) => {
                            const zone = zoneFor(history[index].risk_score);
                            const isHovered = hovered === index;
                            const scanIdAt = history[index].scan_id;
                            const isCurrent = Boolean(scanIdAt) && scanIdAt === currentScanId;
                            const clickable = Boolean(scanIdAt) && !isCurrent;
                            const isProblem = history[index].status === "partial" || history[index].status === "failed";
                            return (
                                <span
                                    key={index}
                                    tabIndex={0}
                                    role={clickable ? "link" : undefined}
                                    aria-label={`${history[index].date}: risk ${history[index].risk_score}, ${zone.label}${isCurrent ? " (this scan)" : clickable ? ". Open this scan" : ""}`}
                                    aria-current={isCurrent ? "page" : undefined}
                                    onMouseEnter={() => setHovered(index)}
                                    onMouseLeave={() => setHovered(null)}
                                    onFocus={() => setHovered(index)}
                                    onBlur={() => setHovered(null)}
                                    onClick={() => openPoint(index)}
                                    onKeyDown={(e) => { if (e.key === "Enter") openPoint(index); }}
                                    className={cn(
                                        "pointer-events-auto absolute flex size-6 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full outline-none",
                                        clickable ? "cursor-pointer" : "cursor-default"
                                    )}
                                    style={{ left: `${(p.x / width) * 100}%`, top: `${(p.y / height) * 100}%` }}
                                >
                                    <span
                                        className={cn(
                                            "rounded-full transition-[width,height]",
                                            isCurrent ? "ring-2 ring-white" : "ring-2 ring-[#0b1625]",
                                            isHovered || isCurrent ? "size-3.5" : "size-2.5"
                                        )}
                                        style={{ backgroundColor: isProblem ? PROBLEM_COLOR : zone.color }}
                                    />
                                </span>
                            );
                        })}
                    </div>
                    {hovered !== null && <RiskPointTooltip history={history} index={hovered} x={points[hovered].x / width} y={points[hovered].y / height} currentScanId={currentScanId} selectMode={Boolean(onSelect)} />}

                    <div className="absolute inset-x-0 bottom-0 flex justify-between text-[9px] text-muted-foreground">
                        {history.map((item, index) => (
                            <span key = {index}>{index > 0 && history[index - 1].date === item.date ? "" : item.date}</span>
                        ))}
                </div>
            </div>
        </div>
    );
}

const LIST_PAGE_SIZE = 100;
async function fetchAllPages<T>(fetchPage: (offset: number) => Promise<T[]>): Promise<T[]> {
    const all: T[] = [];
    for (let offset = 0; offset < 5000; offset += LIST_PAGE_SIZE) {
        const page = await fetchPage(offset);
        all.push(...page);
        if (page.length < LIST_PAGE_SIZE) break;
    }
    return all;
}

type OverviewSeverity = "critical" | "high" | "medium" | "low" | "info";
const OVERVIEW_SEVERITIES: OverviewSeverity[] = ["critical", "high", "medium", "low", "info"];
const OVERVIEW_SEVERITY_WEIGHT: Record<OverviewSeverity, number> = { critical: 40, high: 20, medium: 8, low: 3, info: 1 };
const SEVERITY_STRIPE: Record<OverviewSeverity, string> = {
    critical: "border-l-[#ef4444]", high: "border-l-[#f97316]", medium: "border-l-[#facc15]", low: "border-l-[#3b82f6]", info: "border-l-[#64748b]",
};
const SEVERITY_ROW_BORDER: Record<OverviewSeverity, string> = {
    critical: "border-[#ef4444]/45", high: "border-[#f97316]/45", medium: "border-[#facc15]/45", low: "border-[#3b82f6]/45", info: "border-[#64748b]/45",
};
const SEVERITY_TEXT_CLASS: Record<OverviewSeverity, string> = {
    critical: "text-[#ef4444]", high: "text-[#f97316]", medium: "text-[#facc15]", low: "text-[#60a5fa]", info: "text-[#94a3b8]",
};
const SEVERITY_BAR_CLASS: Record<OverviewSeverity, string> = {
    critical: "bg-[#ef4444]", high: "bg-[#f97316]", medium: "bg-[#facc15]", low: "bg-[#3b82f6]", info: "bg-[#64748b]",
};
const normalizeOverviewSeverity = (value: string): OverviewSeverity =>
    (OVERVIEW_SEVERITIES as string[]).includes(value.toLowerCase()) ? value.toLowerCase() as OverviewSeverity : "info";

interface TopFinding {
    key: string;
    title: string;
    severity: OverviewSeverity;
    ids: string[];
    assets: string[];
    maxCvss: number | null;
    cveId: string | null;
}

function rankFindings(findings: DashboardFindingItem[]): TopFinding[] {
    const merged = new Map<string, TopFinding>();
    for (const f of findings) {
        const severity = normalizeOverviewSeverity(f.severity);
        const key = `${severity}|${f.title}`;
        const entry = merged.get(key) ?? { key, title: f.title, severity, ids: [], assets: [], maxCvss: null, cveId: null };
        entry.ids.push(f.id);
        if (f.asset_identifier && !entry.assets.includes(f.asset_identifier)) entry.assets.push(f.asset_identifier);
        if (f.cvss_score != null && (entry.maxCvss === null || f.cvss_score > entry.maxCvss)) entry.maxCvss = f.cvss_score;
        entry.cveId = entry.cveId ?? f.cve_id ?? null;
        merged.set(key, entry);
    }
    return [...merged.values()].sort((a, b) =>
        OVERVIEW_SEVERITY_WEIGHT[b.severity] - OVERVIEW_SEVERITY_WEIGHT[a.severity]
        || (b.maxCvss ?? -1) - (a.maxCvss ?? -1)
        || b.ids.length - a.ids.length
        || a.title.localeCompare(b.title));
}

interface RiskyAsset {
    asset: DashboardAssetItem;
    counts: Record<OverviewSeverity, number>;
    total: number;
    risk: number;
}

function rankAssets(assets: DashboardAssetItem[], findings: DashboardFindingItem[]): RiskyAsset[] {
    const byAsset = new Map<string, DashboardFindingItem[]>();
    for (const f of findings) if (f.asset_identifier) byAsset.set(f.asset_identifier, [...(byAsset.get(f.asset_identifier) ?? []), f]);
    return assets.map((asset) => {
        const counts: Record<OverviewSeverity, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
        for (const f of byAsset.get(asset.identifier) ?? []) counts[normalizeOverviewSeverity(f.severity)] += 1;
        const total = OVERVIEW_SEVERITIES.reduce((n, s) => n + counts[s], 0);
        const risk = OVERVIEW_SEVERITIES.reduce((n, s) => n + counts[s] * OVERVIEW_SEVERITY_WEIGHT[s], 0);
        return { asset, counts, total, risk };
    })
        .filter((a) => a.total > 0)
        .sort((a, b) => b.risk - a.risk || b.total - a.total || a.asset.identifier.localeCompare(b.asset.identifier));
}

export default function ScanResultsOverview({scanId}: {scanId: string}) {
    const [metrics, setMetrics] = useState<ScanMetrics | null>(null);
    const [allFindings, setAllFindings] = useState<DashboardFindingItem[]>([]);
    const [allAssets, setAllAssets] = useState<DashboardAssetItem[]>([]);
    const [graph, setGraph] = useState<ScanGraphResponse | null>(null);
    const [compare, setCompare] = useState<GraphCompareResponse | null>(null);
    const [openFindingId, setOpenFindingId] = useState<string | null>(null);
    const [openAssetId, setOpenAssetId] = useState<string | null>(null);
    const closeFinding = useCallback(() => setOpenFindingId(null), []);
    const closeAsset = useCallback(() => setOpenAssetId(null), []);
    const [riskHistory, setRiskHistory] = useState<RiskHistoryItem[]>([]);
    const [scanHistory, setScanHistory] = useState<ScanHistoryItem[]>([]);
    const [chartView, setChartView] = useState<ChartView | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        Promise.all([
            fetchScanMetrics(scanId),
            fetchAllPages((offset) => fetchScanFindings(scanId, { limit: LIST_PAGE_SIZE, offset })),
            fetchAllPages((offset) => fetchScanAssets(scanId, { limit: LIST_PAGE_SIZE, offset })),
            fetchScanRiskHistory(scanId),
        ])
        .then(([metricsResults, findingsResult, assetsResult, riskHistoryResult]) => {
            setMetrics(metricsResults);
            setAllFindings(findingsResult);
            setAllAssets(assetsResult);
            setRiskHistory(riskHistoryResult);

        })
        .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load scan results"));
        fetchScanGraph(scanId).then(setGraph).catch(() => {});
        fetchScanHistory()
            .then((history) => {
                setScanHistory(history);
                const current = history.find((h) => h.id === scanId);
                const previous = current && history
                    .filter((h) => h.id !== scanId && h.domain === current.domain && h.created_at < current.created_at)
                    .sort((x, y) => (x.created_at < y.created_at ? 1 : -1))[0];
                return previous ? fetchScanGraphCompare(scanId, previous.id).then(setCompare) : undefined;
            })
            .catch(() => {});
    }, [scanId]);
    const insights = useMemo(() => buildInsights(graph, allAssets), [graph, allAssets]);
    if (error) {
        return (
            <div className="min-w-0" data-scan-id={scanId}>
                <p className="mt-[15px] text-xs text-muted-foreground"> {error} </p>
            </div>
        );
    }

    if(!metrics) {
        return (
            <div className="min-w-0" data-scan-id={scanId}>
                <p className="mt-[15px] text-xs text-muted-foreground"> Loading scan results... </p>
            </div>
        );
    }

    const topFindings = rankFindings(allFindings).slice(0, 5);
    const riskyAssets = rankAssets(allAssets, allFindings);
    const topAssets = riskyAssets.slice(0, 5);
    const viewAllLink = "inline-flex items-center gap-0.5 text-[11px] text-brand-cyan no-underline hover:underline";
    const rowLink = "group grid min-h-10 items-center gap-3 rounded-md px-2 text-[12px] no-underline transition-colors hover:bg-white/[0.04]";

    const countBy = (values: string[]) => {
        const counts = new Map<string, number>();
        values.forEach((v) => counts.set(v, (counts.get(v) ?? 0) + 1));
        return [...counts.entries()].sort((x, y) => y[1] - x[1]).map(([label, value]) => ({ label, value }));
    };
    const assetTypeKeys = Object.keys(metrics.assets).filter((k) => k !== "total");
    const assetItems = assetTypeKeys.map((k) => ({ label: typeLabel(k), value: metrics.assets[k] }));
    const assetColors = assetTypeKeys.map((k) => TYPE_COLOR[typeKey(k)] ?? "#c084fc");
    const subdomainCount = allAssets.filter((a) => typeKey(a.asset_type) === "subdomain").length;
    const ipCount = allAssets.filter((a) => isIpType(a.asset_type)).length;
    const serviceNodes = graph?.nodes.filter((n) => n.type === "service") ?? [];
    const serviceName = (label: string) => {
        const name = (label.split(" :")[0] ?? "").trim();
        return !name || name.toLowerCase() === "tcpwrapped" ? "Unknown" : name.toUpperCase();
    };
    const serviceItems = serviceNodes.length > 0
        ? countBy(serviceNodes.map((n) => serviceName(n.label)))
        : Object.entries(metrics.services).filter(([k]) => k !== "total").map(([k, v]) => ({ label: k.toUpperCase(), value: v }));
    const serviceHostCount = new Set((graph?.edges ?? []).filter((e) => e.type === "EXPOSES").map((e) => e.source)).size;
    const techNodes = graph?.nodes.filter((n) => n.type === "technology") ?? [];
    const technologyItems = techNodes.length > 0
        ? countBy(techNodes.map((n) => n.label))
        : Object.entries(metrics.technologies).filter(([k]) => k !== "total").map(([k, v]) => ({ label: capitalize(k), value: v }));
    const techPortCount = new Set((graph?.edges ?? []).filter((e) => e.type === "RUNS").map((e) => e.source)).size;
    const SERVICE_COLORS = ["#a855f7", "#c084fc", "#7c3aed", "#d8b4fe", "#6d28d9", "#e9d5ff"];
    const TECH_COLORS = ["#4ade80", "#22c55e", "#86efac", "#16a34a", "#bbf7d0", "#15803d"];
    const deltaFor = (prefix: string) => compare
        ? { value: compare.added_nodes.filter((id) => id.startsWith(prefix)).length - compare.removed_nodes.filter((id) => id.startsWith(prefix)).length }
        : null;
    const urgent = metrics.findings.critical + metrics.findings.high;
    const drivers = (["critical", "high", "medium", "low"] as const)
        .filter((sev) => metrics.findings[sev] > 0)
        .map((sev) => `${metrics.findings[sev]} ${capitalize(sev)}`);
    const currentScan = scanHistory.find((h) => h.id === scanId);
    const activeChartView: ChartView = chartView ?? (currentScan?.scan_type === "passive_ctem" ? "passive" : "active");
    const typedHistory: RiskHistoryItem[] | null = currentScan
        ? scanHistory
            .filter((h) => h.domain.toLowerCase() === currentScan.domain.toLowerCase()
                && h.scan_type === CHART_SCAN_TYPE[activeChartView]
                && (h.status === "completed" || h.status === "partial" || h.status === "failed"))
            .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
            .map((h) => ({
                scan_id: h.id,
                status: h.status,
                date: new Date(h.created_at).toLocaleDateString("en-US", { month: "short", day: "2-digit" }),
                risk_score: Math.min(100, h.critical_count * 25 + h.high_count * 15 + h.medium_count * 5 + h.low_count),
                total_findings: h.total_findings,
            }))
        : null;

    const latestHistory = riskHistory[riskHistory.length - 1];
    const riskTrend = riskHistory.length >= 2 && latestHistory.risk_score === metrics.risk_score
        ? latestHistory.risk_score - riskHistory[riskHistory.length - 2].risk_score
        : null;

    return (
        <div className="min-w-0" data-scan-id={scanId}>
            <section className="mb-4 grid grid-cols-[minmax(200px,1.1fr)_repeat(4,minmax(180px,1fr))] gap-3.5 max-[1300px]:grid-cols-3 max-[950px]:grid-cols-2 max-[650px]:gap-2.5">
                <article className={cn(PANEL_CLASS_NAME, "flex flex-col border border-transparent max-[650px]:col-span-2 max-[650px]:p-3")}>
                    <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px] font-semibold text-[#cbd5e1] uppercase">Risk Score</span>
                    </div>
                    <RiskGauge score={metrics.risk_score} />
                    <p className="m-0 -mt-1 text-center">
                        <strong className={cn("text-[28px] leading-none", riskLevelColorClass(metrics.risk_level))}>{metrics.risk_score}</strong>
                        <span className="text-[12px] text-muted-foreground">/100</span>
                    </p>
                    <p className={cn("m-0 mt-1 text-center text-[11px] font-semibold uppercase", riskLevelColorClass(metrics.risk_level))}>
                        {riskLevelLabel(metrics.risk_level)}
                    </p>
                    <p className="m-0 mt-2 text-center text-[11px] text-[#94a3b8]">
                        {drivers.length > 0 ? <>Driven by {drivers.join(" · ")}</> : "No scored findings"}
                    </p>
                    {riskTrend !== null && (
                        <p className={cn("m-0 mt-1 text-center text-[11px] font-semibold",
                            riskTrend > 0 ? "text-brand-alert" : riskTrend < 0 ? "text-brand-success" : "text-[#94a3b8]")}>
                            {riskTrend === 0 ? "No change" : `${riskTrend > 0 ? "▲" : "▼"} ${Math.abs(riskTrend)}`}
                            <span className="font-normal text-[#64748b]"> since last scan</span>
                        </p>
                    )}
                </article>

                <SummaryCard
                    layout="compact"
                    title="Findings"
                    icon={Bug}
                    accentClassName="bg-brand-alert/10 text-brand-alert"
                    value={metrics.findings.total}
                    items={(["critical", "high", "medium", "low", "info"] as const).map((sev) => ({ label: capitalize(sev), value: metrics.findings[sev] }))}
                    colors={[FINDINGS_COLORS.critical, FINDINGS_COLORS.high, FINDINGS_COLORS.medium, FINDINGS_COLORS.low, FINDINGS_COLORS.info]}
                    subtitle={urgent > 0
                        ? <span className="text-brand-alert">{urgent} critical/high need attention</span>
                        : "No critical or high findings"}
                    delta={deltaFor("finding:") && { ...deltaFor("finding:")!, upIsBad: true }}
                />

                <SummaryCard
                    layout="compact"
                    title="Assets"
                    icon={Globe}
                    accentClassName="bg-brand-cyan/10 text-brand-cyan"
                    value={metrics.assets.total ?? 0}
                    items={assetItems}
                    colors={assetColors}
                    subtitle={`${subdomainCount} subdomain${subdomainCount === 1 ? "" : "s"} · ${ipCount} IP${ipCount === 1 ? "" : "s"}`}
                    delta={deltaFor("asset:")}
                />

                <SummaryCard
                    layout="compact"
                    title="Services"
                    icon={Network}
                    accentClassName="bg-[#a855f7]/10 text-[#c084fc]"
                    value={metrics.services.total ?? 0}
                    items={serviceItems}
                    colors={serviceItems.map((_, i) => SERVICE_COLORS[i % SERVICE_COLORS.length])}
                    subtitle={serviceHostCount > 0 ? `Open ports on ${serviceHostCount} host${serviceHostCount === 1 ? "" : "s"}` : "Open ports"}
                    delta={deltaFor("service:")}
                />

                <SummaryCard
                    layout="compact"
                    title="Technologies"
                    icon={Layers}
                    accentClassName="bg-brand-success/10 text-brand-success"
                    value={metrics.technologies.total ?? 0}
                    items={technologyItems}
                    colors={technologyItems.map((_, i) => TECH_COLORS[i % TECH_COLORS.length])}
                    subtitle={techPortCount > 0 ? `Across ${techPortCount} port${techPortCount === 1 ? "" : "s"}` : "Detected products"}
                    delta={deltaFor("technology:")}
                />
            </section>

            <section className="grid grid-cols-[1.15fr_1.1fr_1.15fr] gap-3.5 max-[1300px]:grid-cols-2 max-[950px]:grid-cols-1">
                <article className = {cn(PANEL_CLASS_NAME, "min-h-[280px] max-[1300px]:col-span-full")}>
                    <div className="mb-[18px] flex flex-wrap items-center justify-between gap-4">
                        <div>
                            <h2 className="m-0 text-[13px] text-foreground uppercase">Risk Over Time</h2>
                            {typedHistory && (
                                <span className="text-xs text-muted-foreground">
                                    {typedHistory.length} {activeChartView} scan{typedHistory.length === 1 ? "" : "s"} of this domain
                                </span>
                            )}
                        </div>
                        {typedHistory && (
                            <div role="tablist" aria-label="Scan type" className="inline-flex rounded-lg border border-brand-panel-border bg-brand-panel-deep p-0.5">
                                {(["active", "passive"] as const).map((option) => (
                                    <button
                                        key={option}
                                        type="button"
                                        role="tab"
                                        aria-selected={activeChartView === option}
                                        onClick={() => setChartView(option)}
                                        className={cn(
                                            "rounded-md px-2.5 py-1 text-xs font-medium capitalize transition-colors",
                                            activeChartView === option
                                                ? option === "active" ? "bg-brand-cyan/15 text-brand-cyan" : "bg-[#a78bfa]/15 text-[#a78bfa]"
                                                : "text-muted-foreground hover:text-foreground"
                                        )}
                                    >
                                        {option}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {typedHistory && typedHistory.length < 2 ? (
                        <p className="mt-[15px] text-xs text-muted-foreground">
                            {typedHistory.length === 0 ? `No ${activeChartView} scans of this domain yet.` : `Run another ${activeChartView} scan to see a trend.`}
                        </p>
                    ) : (
                        <RiskHistoryChart history={typedHistory ?? riskHistory} currentScanId={scanId} />
                    )}
                </article>

                <CollapsiblePanel
                    title="Most Severe Findings"
                    icon={ShieldAlert}
                    iconClassName="bg-brand-alert/10 text-brand-alert"
                    action={<Link href={`/phase2_scan/results/${scanId}/findings`} className={viewAllLink}>View all {allFindings.length} <ChevronRight className="size-3.5" /></Link>}
                >
                    {topFindings.length === 0 ? (
                        <p className="mt-[15px] text-xs text-muted-foreground">No findings — nothing to fix 🎉</p>
                    ) : (
                        <div className="grid gap-1.5">
                            {topFindings.map((finding) => (
                                <button
                                    key={finding.key}
                                    type="button"
                                    onClick={() => setOpenFindingId(finding.ids[0])}
                                    aria-haspopup="dialog"
                                    title={finding.title}
                                    className={cn(rowLink, "w-full grid-cols-[minmax(0,1fr)_minmax(0,auto)_auto] border border-l-[3px] bg-transparent text-left", SEVERITY_ROW_BORDER[finding.severity], SEVERITY_STRIPE[finding.severity])}
                                >
                                    <span className="flex min-w-0 items-center gap-1.5 text-foreground">
                                        <span className="truncate">{finding.title}</span>
                                        {finding.ids.length > 1 && <span className="shrink-0 text-[10px] text-[#94a3b8]">×{finding.ids.length}</span>}
                                        {finding.cveId && <span className="shrink-0 rounded-[4px] border border-[#26364e] px-1 text-[9px] text-[#9eacbd]">{finding.cveId}</span>}
                                        {finding.maxCvss !== null && <span className="shrink-0 rounded-[4px] border border-[#26364e] px-1 text-[9px] text-[#9eacbd]">CVSS {finding.maxCvss}</span>}
                                    </span>
                                    <span className="max-w-[140px] truncate text-[11px] text-[#94a3b8] max-[650px]:hidden">
                                        {finding.assets.length === 1 ? finding.assets[0] : finding.assets.length > 1 ? `${finding.assets.length} assets` : ""}
                                    </span>
                                    <span className={cn("rounded-[5px] border px-2 py-0.5 text-[9px] font-semibold uppercase", severityClassName[finding.severity] ?? "border-[#334155] text-[#94a3b8]")}>
                                        {capitalize(finding.severity)}
                                    </span>
                                </button>
                            ))}
                        </div>
                    )}
                </CollapsiblePanel>

                <CollapsiblePanel
                    title="Top Assets by Risk"
                    icon={Target}
                    iconClassName="bg-brand-cyan/10 text-brand-cyan"
                    action={<Link href={`/phase2_scan/results/${scanId}/assets`} className={viewAllLink}>View all {allAssets.length} <ChevronRight className="size-3.5" /></Link>}
                >
                    {topAssets.length === 0 ? (
                        <p className="mt-[15px] text-xs text-muted-foreground">{allAssets.length === 0 ? "No assets discovered yet." : "No assets with findings."}</p>
                    ) : (
                        <div className="grid gap-1.5">
                            {topAssets.map(({ asset, counts, total }) => {
                                const present = OVERVIEW_SEVERITIES.filter((sev) => counts[sev] > 0);
                                const worst = present[0] ?? "info";
                                return (
                                    <button
                                        key={asset.id}
                                        type="button"
                                        onClick={() => setOpenAssetId(asset.id)}
                                        aria-haspopup="dialog"
                                        className={cn(rowLink, "w-full grid-cols-[minmax(0,1fr)_auto_minmax(110px,auto)] border border-l-[3px] bg-transparent text-left max-[650px]:grid-cols-[minmax(0,1fr)_auto]", SEVERITY_ROW_BORDER[worst], SEVERITY_STRIPE[worst])}
                                    >
                                        <span className="truncate text-foreground" title={asset.identifier}>{asset.identifier}</span>
                                        <TypeBadge type={asset.asset_type} />
                                        <span className="flex flex-col gap-1 max-[650px]:hidden">
                                            <span className="flex flex-wrap gap-x-1.5 text-[11px] font-semibold">
                                                {present.map((sev) => <span key={sev} className={SEVERITY_TEXT_CLASS[sev]}>{counts[sev]} {capitalize(sev)}</span>)}
                                            </span>
                                            <span className="flex h-1 w-full overflow-hidden rounded-full bg-white/5">
                                                {present.map((sev) => <span key={sev} className={SEVERITY_BAR_CLASS[sev]} style={{ width: `${(counts[sev] / total) * 100}%` }} />)}
                                            </span>
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </CollapsiblePanel>
    </section>

    {openFindingId && (() => {
        const finding = allFindings.find((f) => f.id === openFindingId);
        return finding ? <FindingDetails finding={finding} scanId={scanId} onClose={closeFinding} showViewInFindings /> : null;
    })()}
    {openAssetId && (() => {
        const asset = allAssets.find((a) => a.id === openAssetId);
        return asset ? (
            <AssetDetails
                asset={asset}
                scanId={scanId}
                info={insights.get(asset.id)}
                findings={allFindings.filter((f) => f.asset_identifier === asset.identifier)}
                onOpenAsset={setOpenAssetId}
                onClose={closeAsset}
            />
        ) : null;
    })()}
</div>
);}

function CollapsiblePanel({title, icon: Icon, iconClassName, action, children}: {title: string; icon?: LucideIcon; iconClassName?: string; action?: React.ReactNode; children: React.ReactNode}) {
    const [open, setOpen] = useState(false);
    return (
        <article className={cn(PANEL_CLASS_NAME, "min-h-[280px] max-sm:min-h-0")}>
            <div className={cn("relative flex items-center justify-between gap-4", open ? "mb-[18px]" : "sm:mb-[18px]")}>
                <h2 className="m-0 flex items-center gap-2 text-[13px] text-foreground uppercase">
                    {Icon && (
                        <span className={cn("grid size-7 shrink-0 place-items-center rounded-lg", iconClassName)}>
                            <Icon aria-hidden="true" className="size-4" />
                        </span>
                    )}
                    <button
                        type="button"
                        onClick={() => setOpen((prev) => !prev)}
                        aria-expanded={open}
                        className="border-0 bg-transparent p-0 text-left text-inherit uppercase after:absolute after:inset-0 after:content-[''] sm:pointer-events-none"
                    >
                        {title}
                    </button>
                </h2>
                <span className="relative z-10 flex items-center gap-3">
                    {action}
                    <ChevronDown aria-hidden="true" className={cn("pointer-events-none size-4 text-muted-foreground transition-transform sm:hidden", open && "rotate-180")} />
                </span>
            </div>
            <div className={cn(!open && "max-sm:hidden")}>{children}</div>
        </article>
    );
}