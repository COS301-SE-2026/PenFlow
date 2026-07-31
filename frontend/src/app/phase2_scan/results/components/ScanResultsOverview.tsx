"use client";
import {useEffect, useState} from "react";
import Link from "next/link";
import { Chart as ChartJS, ArcElement, Tooltip, Legend, type ChartOptions} from "chart.js";
import { Doughnut } from "react-chartjs-2";
import { capitalize, cn } from "@/lib/utils";
import{fetchScanMetrics, fetchScanFindings, fetchScanAssets,fetchScanRiskHistory,
    type ScanMetrics,
    type DashboardFindingItem,
    type DashboardAssetItem,
    type RiskHistoryItem,
} from "@/lib/scanService";

ChartJS.register(ArcElement, Tooltip ,Legend);

interface BreakdownItem {
    label: string;
    value: number;
}

interface SummaryCardProps {
    title: string;
    value: number;
    items: BreakdownItem[];
    colors: string[];
}

const severityClassName: Record<string, string> = {
    critical: "border-[#991b1b] text-brand-alert bg-brand-alert/10",
    high: "border-brand-orange/70 text-brand-orange bg-brand-orange/10",
    medium: "border-brand-yellow/70 text-brand-yellow bg-brand-yellow/10",
    low: "border-[#1e40af] text-[#60a5fa] bg-[#1e40af]/10",
};

const FINDINGS_COLORS: Record<string, string> = {
    critical: "#ef4444",
    high: "#f97316",
    medium: "#facc15",
    low: "#3b82f6",
    info: "#64748b",
};

const BREAKDOWN_PALETTE = ["#3b82f6", "#14b8a6", "#22c55e", "#f59e0b", "#a855f7", "#ec4899", "#64748b"];


function paletteColors(count: number): string[] {
    return Array.from({length: count}, (_, i) => BREAKDOWN_PALETTE[i % BREAKDOWN_PALETTE.length]);
}

const donutTooltipOptions: ChartOptions<"doughnut">["plugins"] = {
    legend: {display: false},
    tooltip: {
        backgroundColor: "#091628",
        borderColor: "rgba(43,180,220,0.3)",
        borderWidth: 1,
        titleColor: "#e5f3ff",
        bodyColor: "#e5f3ff",
        padding: 8,
    },
};

const donutOptions: ChartOptions<"doughnut"> = {
    cutout: "62%",
    plugins: donutTooltipOptions,
    maintainAspectRatio: false,
};

const PANEL_CLASS_NAME = "min-w-0 rounded-[10px] border-brand-panel-border bg-[#0b1625] p-[18px]";
function SummaryCard({title, value, items, colors}: SummaryCardProps) {
    const total = items.reduce((sum, item) => sum + item.value, 0);
    return (
        <article className={cn(PANEL_CLASS_NAME, "min-h-[210px]")}>
            <div className="flex items-center justify-between gap-4">
                <div>
                    <span className="mb-2 block text-[11px] font-semibold text-[#cbd5e1] uppercase">{title}</span>
                    <strong className="block text-[30px] leading-none text-foreground"> {value} </strong>
                </div>
                {total > 0 && (
                    <div className="size-[74px] shrink-0">
                        <Doughnut data = {{
                            labels: items.map((item) => item.label),
                            datasets: [{
                                data: items.map((item) => item.value),
                                backgroundColor: colors,
                                borderWidth: 0,
                            }],
                        }}
                        options = {donutOptions}
                    />
                    </div>
                )}
            </div>

            {total > 0 ? (
                <ul className="mt-[15px] grid list-none gap-1.5 p-0">
                    {items.map((item, index) => (
                        <li key = {item.label} className="flex justify-between gap-3 text-[11px]">
                            <span style={{color: colors[index]}}> {item.label} </span>
                            <strong className="text-foreground"> {item.value} </strong>
                        </li>
                    ))}
                </ul>
            ): (
                <p className="mt-[15px] text-xs text-muted-foreground">No breakdown available yet.</p>
            )}
        </article>
    );
}

function riskLevelLabel(level: string): string {
    return level.split("_").map((word) => capitalize(word.toLowerCase())).join(" ");
}

function riskLevelColorClass(level: string): string {
    const normalized = level.toUpperCase();
    if (normalized === "HIGH") return "text-brand-alert";
    if (normalized === "MEDIUM") return "text-brand-yellow";
    return "text-brand-success";
}

const RISK_GAUGE_COLORS = {safe: "#4ade80", risk: "#ff5f4e"};

const riskGaugeOptions: ChartOptions<"doughnut"> = {
    rotation: -90,
    circumference: 180,
    cutout: "75%",
    plugins: donutTooltipOptions,
    maintainAspectRatio: false,
};

function RiskGauge({score}: {score: number}) {
    const clamped = Math.max(0, Math.min(100, score));
    return (
        <div className="relative mx-auto mt-[10px] h-[105px] w-[180px] overflow-hidden">
            <div className="absolute inset-x-0 top-0 h-[180px]">
                <Doughnut
                    data={{
                        labels: ["Safe", "Risk"],
                        datasets: [{
                            data: [100 - clamped, clamped],
                            backgroundColor: [RISK_GAUGE_COLORS.safe, RISK_GAUGE_COLORS.risk],
                            borderWidth: 0,
                        }],
                    }}
                    options={riskGaugeOptions}
                />
            </div>
        </div>
    );
}

function BreakdownItems(breakdown: Record<string, number>) : BreakdownItem[] {
    return Object.entries(breakdown).filter(([key]) => key !== "total").map(([Key, value]) => ({label:capitalize(Key), value}));
}

function RiskHistoryChart({history}: {history: RiskHistoryItem[]}) {
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
    const fillPoints = `${linePoints} ${width}, ${height} 0,${height}`;

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
                        <polyline
                            points = {linePoints}
                            className="fill-none stroke-[#ef4444]"
                            style = {{strokeWidth: 4, vectorEffect: "non-scaling-stroke"}}
                        />
                        <polygon points={fillPoints} fill = "rgb(239 68 68 / 10%)" />
                        {points.map((p, index) => (
                            <circle key = {`${p.x}-${p.y}`} cx={p.x} cy={p.y} r="5" fill="#ef4444">
                                <title>{history[index].date}</title>
                            </circle>
                        ))}
                    </svg>

                    <div className="absolute inset-x-0 bottom-0 flex justify-between text-[9px] text-muted-foreground">
                        {history.map((item) => (
                            <span key = {item.date}>{item.date}</span>
                        ))}
                </div>
            </div>
        </div>
    );
}

export default function ScanResultsOverview({scanId}: {scanId: string}) {
    const [metrics, setMetrics] = useState<ScanMetrics | null>(null);
    const [topFindings, setTopFindings] = useState<DashboardFindingItem[]>([]);
    const [topAssets, setTopAssets] = useState<DashboardAssetItem[]>([]);
    const [riskHistory, setRiskHistory] = useState<RiskHistoryItem[]>([]);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        Promise.all([
            fetchScanMetrics(scanId),
            fetchScanFindings(scanId, {limit:5}),
            fetchScanAssets(scanId, {limit:5}),
            fetchScanRiskHistory(scanId),
        ])
        .then(([metricsResults, findingsResult, assetsResult, riskHistoryResult]) => {
            setMetrics(metricsResults);
            setTopFindings(findingsResult);
            setTopAssets(assetsResult);
            setRiskHistory(riskHistoryResult);

        })
        .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load scan results"));
    }, [scanId]);
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

    const assetItems = BreakdownItems(metrics.assets);
    const serviceItems = BreakdownItems(metrics.services);
    const technologyItems = BreakdownItems(metrics.technologies);

    return (
        <div className="min-w-0" data-scan-id={scanId}>
            <section className="mb-4 grid grid-cols-[minmax(190px,1.15fr)_repeat(4,minmax(180px,1fr))] gap-3.5 max-[1300px]:grid-cols-3 max-[950px]:grid-cols-2 max-[650px]:grid-cols-1">
                <article className={cn(PANEL_CLASS_NAME, "flex min-h-[210px] flex-col")}>
                    <span className="mb-2 block text-[11px] font-semibold text-[#cbd5e1] uppercase">Risk Score</span>
                        <div className="relative">
                            <RiskGauge score = {metrics.risk_score} />
                            <div className="pointer-events-none absolute inset-x-0 bottom-[3px] text-center">
                            <strong className={cn("text-[30px]", riskLevelColorClass(metrics.risk_level))}>{metrics.risk_score}</strong>

                            <span className="text-muted-foreground">/100</span>
                        </div>
                    </div>

                    <p className={cn("mt-2.5 text-center text-[11px] font-semibold text-brand-alert uppercase", riskLevelColorClass(metrics.risk_level))}>
                        {riskLevelLabel(metrics.risk_level)}
                    </p>
                </article>

                <SummaryCard
                    title = "Findings"
                    value = {metrics.findings.total}
                    items = {[
                        {label: "Critical", value: metrics.findings.critical},
                        {label: "High", value: metrics.findings.high},
                        {label: "Medium", value: metrics.findings.medium},
                        {label: "Low", value: metrics.findings.low},
                        {label: "Info", value: metrics.findings.info},
                    ]}
                    colors={[FINDINGS_COLORS.critical, FINDINGS_COLORS.high, FINDINGS_COLORS.medium, FINDINGS_COLORS.low, FINDINGS_COLORS.info]}
                />

                <SummaryCard
                    title = "Assets"
                    value = {metrics.assets.total ?? 0}
                    items = {assetItems}
                    colors = {paletteColors(assetItems.length)}
                />

                <SummaryCard
                    title = "Services"
                    value = {metrics.services.total ?? 0}
                    items = {serviceItems}
                    colors = {paletteColors(serviceItems.length)}
                />

                <SummaryCard
                    title = "Technologies"
                    value = {metrics.technologies.total ?? 0}
                    items = {technologyItems}
                    colors = {paletteColors(technologyItems.length)}
                />
            </section>

            <section className="grid grid-cols-[1.15fr_1.1fr_1.15fr] gap-3.5 max-[1300px]:grid-cols-2 max-[950px]:grid-cols-1">
                <article className = {cn(PANEL_CLASS_NAME, "min-h-[280px] max-[1300px]:col-span-full")}>
                    <div className="mb-[18px] flex items-center justify-between gap-4">
                        <h2 className="m-0 text-[13px] text-foreground uppercase">Risk Over Time</h2>
                    </div>

                    <RiskHistoryChart history={riskHistory} />
                </article>

                <article className={cn(PANEL_CLASS_NAME, "min-h-[280px]")}>
                    <div className="mb-[18px] flex items-center justify-between gap-4">
                        <h2 className="m-0 text-[13px] text-foreground uppercase">Top Critical Findings</h2>
                        <Link href={`/phase2_scan/results/${scanId}/findings`} className="text-[11px] text-brand-cyan no-underline">
                            View all findings
                        </Link>
                    </div>

                    {topFindings.length === 0 ? (
                        <p className="mt-[15px] text-xs text-muted-foreground">No findings yet.</p>  
                    ): (
                        <div className="grid">
                            {topFindings.map((finding) => (
                                <div className="grid min-h-[42px] grid-cols-[minmax(140px,1.7fr)_minmax(90px,1fr)_auto_34px] items-center gap-3 border-b border-brand-panel-border/70 text-[11px]
                                                last:border-b-0 max-[650px]:grid-cols-[1fr_auto] max-[650px]:py-2.5"
                                                key={finding.id}
                                >
                                    <span className="overflow-hidden text-ellipsis whitespace-nowrap text-foreground">
                                        {finding.title}
                                    </span>
                                    <span className="text-muted-foreground max-[650px]:hidden">{finding.cve_id ?? "_"}</span>
                                    <span
                                        className={cn("justify-self-start rounded-[5px] border px-2 py-1 text-[9px] font-semibold uppercase",
                                        severityClassName[finding.severity.toLowerCase()]
                                )}
                            >
                                {capitalize(finding.severity)}
                            </span>
                            <strong className="text-foreground">{finding.cvss_score ?? "_"}</strong>
                        </div>
                    ))}
                </div>
            )}
        </article>
        
        <article className={cn(PANEL_CLASS_NAME, "min-h-[280px]")}>
            <div className="mb-[18px] flex items-center justify-between gap-4">
                <h2 className="m-0 text-[13px] text-foreground uppercase">Top Assets by Findings</h2>
                <Link href={`/phase2_scan/results/${scanId}/assets`} className="text-[11px] text-brand-cyan no-underline">
                    View all assets
                </Link>
            </div>

            {topAssets.length === 0 ? (
                <p className="mt-[15px] text-xs text-muted-foreground">No assets discovered yet.</p>
            ): (
                <div className="grid">
                    {topAssets.map((asset)=> (
                        <div className="grid min-h-[42px] grid-cols-[minmax(130px,1fr)_auto_80px] items-center gap-3 border-b border-brand-panel-border/70 text-[11px] last:border-b-0 max-[650px]:grid-cols-[1fr_auto] max-[650px]:py-2.5"
                        key={asset.id}
                    >
                        <span className="overflow-hidden text-ellipsis whitespace-nowrap text-foreground">
                            {asset.identifier}
                        </span>
                        <span className="justify-self-start rounded-[5px] border border-brand-panel-border px-2 py-1 text-[9px] font-semibold uppercase text-muted-foreground">
                            {capitalize(asset.asset_type)}
                        </span>
                        <span className="text-right text-muted-foreground max-[650px]:col-span-full max-[650px]:text-left">
                            {asset.findings_count} findings
                        </span>
                    </div>
                    ))}
                </div>
            )}
        </article>
    </section>
</div>
);}