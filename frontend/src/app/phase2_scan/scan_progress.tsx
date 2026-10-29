"use client";
import type {ReactNode} from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Bug, ChevronDown, ChevronRight, Crosshair, FileSearch, Fingerprint, Globe, Info, Lock, Network, ShieldAlert,
         ShieldCheck, type LucideIcon,} from "lucide-react";

import { Card, CardContent} from "@/components/ui/card";
import {Badge} from "@/components/ui/badge";
import {Button} from "@/components/ui/button";
import {cn} from "@/lib/utils";
import radarStyles from "@/app/scan/components/ScanConsoleSection.module.css";
import {fetchScanStatus, type RealTimeScanStatus} from "@/lib/scanService";
import { Progress } from "@/shared/components/ui/progress";


type SourceStatus = "pending" | "running" | "completed" | "failed" | "partial"| "skipped";
type SourcePhase = "idle" | "line" | "done";
type SourceWithPhase = RealTimeScanStatus["sources"][number] & {
    status: SourceStatus;
    phase: SourcePhase;
};

const POLL_INTERVAL_MS = 4000;
const TERMINAL_SCAN_STATUSES = new Set(["completed", "failed", "partial"]);
const TERMINAL_SOURCE_STATUSES = new Set<SourceStatus>(["completed", "failed", "partial", "skipped"]);
const scanTypeLabel: Record<string, string> = {
    active_vulnerability: "Active Vulnerability Scan",
    passive_ctem: "Passive Reconnaissance",
};

interface SourceMeta {
    label: string;
    description: string;
    icon: LucideIcon;
}

const SOURCE_META: Record<string, SourceMeta> = {
    dns: { label: "DNS", description: "Performs DNS enumeration for the target domain", icon: Network},
    "crt.sh": { label: "crt.sh", description: "Searches Certificate Transparency logs for issued certificates and reaated. ", icon: FileSearch},
    urlscan: { label: "URLScan", description: "Queries urlscan.io for prior scans and page metadata for the domain.", icon: Globe},
    wappalyzer: { label: "Wappalyzer", description: "Identifies web technologies used by the target.", icon: Fingerprint},
    shodan: { label: "Shodan", description: "Queries Shodan for exposed devices, banners, and services tied to the target's IP.", icon: Fingerprint},
    hibp: { label: "HaveIBeenPwned", description: "Checks associated email addresses and domains against known data breach databases", icon: ShieldAlert},
    target_resolution: { label: "Resolving Target", description: "Resolves the verified domain into IPv4 and IPv6 addresses.", icon: Globe},
    nmap: { label: "Discovering ports", description: "Checks whether the host is reachable and discovers open ports and network services.", icon: Crosshair},
    http_security: { label: "Checking HTTP", description: "Inspects HTTP responses and security headers such as CSP and HSTS.", icon: ShieldCheck},
    tls: { label: "Inspecting TLS", description: "Checks certificates, TLS versions, cipher suites, expiry, issuer and self-signed status.", icon: Lock},
    fingerprint: { label: "Detecting Tech", description: "Identifies servers, frameworks, languages, CMS platforms, CDNs and their versions.", icon: Fingerprint},
    cve: { label: "Matching CVEs", description: "Cross-references detected products and versions with vulnerability information and generates CVE findings.", icon: Bug},
};

const DEFAULT_SOURCE_META: SourceMeta = {
    label: "unknown source",
    description: "No description available for this source",
    icon: Info,
};

const ragIndexStatusConfig = {
    pending: {
        label: "Pending",
        className: "border-muted-foreground/30 bg-muted/40 text-muted-foreground",
    },
    indexing: {
        label: "Preparing",
        className: "border-brand-cyan bg-brand-cyan/10 text-brand-cyan",
    },
    ready: {
        label: "Ready",
        className: "border-brand-success bg-brand-success/10 text-brand-success",
    },
    failed: {
        label: "Needs retry",
        className: "border-brand-alert bg-brand-alert/10 text-brand-alert",
    },
} as const;

const lineToneClassName: Record<SourceStatus, string> ={
    pending: "stroke-muted-foreground/25",
    running: "stroke-brand-yellow animate-pulse drop-shadow-[0_0_3px_rgba(245,200,66,0.75)]",
    completed: "stroke-brand-success/60 drop-shadow-[0_0_3px_rgba(74,222,128,0.75)]",
    failed:  "stroke-brand-alert/60 drop-shadow-[0_0_3px_rgba(245,95,78,0.6)]",
    partial: "stroke-brand-yellow/60 drop-shadow-[0_0_3px_rgba(245,200,66,0.6)]",
    skipped: "stroke-muted-foreground/25",
};

const cardClassName = "border border-brand-panel-border bg-brand-panel ring-0";
const sectionTitleClassName = "text-sm font-bold uppercase tracking-[0.15em] text-foreground/90";

function formatElapsed(startIso: string): string {
    const ms = Date.now() - new Date(startIso).getTime();
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}


function ScanRadar({isComplete}:{isComplete:boolean}) {
    const playState = isComplete ? "paused" : "running";
    return (
        <div className = {radarStyles.radarScope} aria-hidden = "true">
            <div className = {`${radarStyles.radarRing} ${radarStyles.r1}`} />
            <div className = {`${radarStyles.radarRing} ${radarStyles.r2}`} />
            <div className = {`${radarStyles.radarRing} ${radarStyles.r3}`} />
            <div className = {radarStyles.radarSweep} style={{animationPlayState: playState}}/>
            <div className = {`${radarStyles.radarDot} ${radarStyles.dotCyan}`} style={{animationPlayState: playState}}/>
            <div className = {`${radarStyles.radarDot} ${radarStyles.dotRed}`} style={{animationPlayState: playState}}/>
            <div className = {`${radarStyles.radarDot} ${radarStyles.dotOrange}`} style={{animationPlayState: playState}}/>
            <div className = {`${radarStyles.radarDot} ${radarStyles.dotBlue}`} style={{animationPlayState: playState}}/>
            <div className = {`${radarStyles.radarDot} ${radarStyles.dotYellow}`} style={{animationPlayState: playState}}/>
        </div>
    );
}

function ScanDetailsBar({scan}: {scan:RealTimeScanStatus}) {
    const [open, setOpen] = useState(false);
    const completedCount = scan.sources.filter((s)=> TERMINAL_SOURCE_STATUSES.has(s.status as SourceStatus)).length;
    const ragIndexState = ragIndexStatusConfig[scan.rag_index_status];
    const items: {label:string; value:ReactNode}[] = [
        {label: "Domain", value: scan.domain},
        {label: "Scan Type", value: scanTypeLabel[scan.scan_type] ?? scan.scan_type},
        {label: "Status",
            value: (<span className= "inline-flex items-center gap-1.5 text-brand-cyan capitalize">
                <span className = "size-1.5 rounded-full bg-brand-cyan"/>
                {scan.status}
            </span>),
        },
        {
            label: "AI Evidence",
            value: (
                <Badge variant="outline" className={ragIndexState.className}>
                    {ragIndexState.label}
                </Badge>
            ),
        },
        {
            label: "Elapsed Time", value: formatElapsed(scan.created_at)},
            {
                label: "Sources Completed",
                value: `${completedCount} / ${scan.sources.length}`,
            },
    ];

    return (
        <Card className = {cardClassName}>
            <CardContent>
                <button
                    type="button"
                    onClick={() => setOpen((prev) => !prev)}
                    aria-expanded={open}
                    className="hidden w-full items-center justify-between gap-3 text-left max-sm:flex"
                >
                    <span className={sectionTitleClassName}>Scan details</span>
                    <ChevronDown aria-hidden="true" className={cn("size-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")}/>
                </button>
                <div className={cn("flex flex-wrap items-center gap-x-8 gap-y-4 max-sm:mt-4", !open && "max-sm:hidden")}>
                {items.map((item,index) => (
                    <div key = {item.label} className = "flex items-center gap-8">
                        <div className = "flex flex-col gap-1">
                            <span className = "text-xs uppercase tracking-wide text-muted-foreground">{item.label}</span>
                            <span className="text-base font-medium whitespace-nowrap text-foreground">{item.value}</span>
                        </div>
                        {index < items.length -1 && <span className ="hidden h-8 w-px bg-brand-panel-border sm:block" />}
                    </div>
                ))}
                </div>
            </CardContent>
        </Card>
    );
}

function SourceCard({
    sourceName,
    status,
    phase,
    totalTargets,
    completedTargets,
    failedTargets,
    compact = false,
}: {
    sourceName: string;
    status: SourceStatus;
    phase: SourcePhase;
    totalTargets: number;
    completedTargets: number;
    failedTargets: number;
    compact?: boolean;
}) {
    const [flipped, setFlipped] = useState(false);
    const meta = SOURCE_META[sourceName] ?? {...DEFAULT_SOURCE_META, label: sourceName};
    const isDone = phase === "done";
    const isFailed = status === "failed";
    
    const isRunning = status === "running";
    const toneClassName = isFailed ? "text-brand-alert" : isRunning ? "text-brand-yellow": "text-brand-success";
    const borderClassName = isDone ? (isFailed ? "border-brand-alert": "border-brand-success") : isRunning ? "border-brand-yellow animate-pulse" : "border-[#2a3f66]"
    const processedTargets = Math.min(completedTargets + failedTargets, totalTargets);
    const targetPercentage = totalTargets > 0 ? Math.round((processedTargets / totalTargets) * 100) : 0;
    const SourceGlyph = meta.icon;

    return (
        <button
            type = "button"
            onClick={() => setFlipped((prev) => !prev)}
            aria-pressed={flipped}
            aria-label = {`${meta.label}: click to ${flipped ? "hide" : "show"} details`}
            className={cn(
                "block w-full cursor-pointer text-left [perspective:800px] transition-[height] duration-500 ease-out",
                compact ? (flipped ? "h-40" : "h-20") : (flipped ? "h-[150px]" : "h-20")
            )}
        >
            <div className={cn(
                "relative h-full w-full transition-transform duration-500 [transform-style:preserve-3d]",
                flipped && "[transform:rotateY(180deg)]"
            )}
            >
                <div className = {cn(
                    "absolute inset-0 flex items-center justify-center gap-2.5 rounded-md border bg-[#102448]/85 px-4 py-3.5 backdrop-blur-sm transition-[box-shadow,border-color] duration-500 [backface-visibility:hidden]",
                    borderClassName, totalTargets > 0 && (compact ? "pb-9" : "pb-7"),
                    compact && "gap-1.5 px-2.5 py-2",
                    isDone && (isFailed ? "shadow-[0_0_10px_1px_rgba(255,95,78,0.2)]": "shadow-[0_0_10px_rgba(74, 222, 128, 0.15)]"),
                    isRunning && "shadow-[0_0_10px_1px_rgba(255,200,66,0.3)]"
                )}
                >
                    <Info className={cn("absolute shrink-0 text-white/85", compact ? "top-1.5 right-1.5 size-3" : "top-2 right-2 size-3.5")}/>
                    <SourceGlyph className = {cn("size-4 shrink-0 transition-colors duration-500", (isDone || isRunning) ? toneClassName : "text-muted-foreground/50")}/>
                    <span
                        className = {cn(
                            "text-center font-heading text-sm leading-tight font-bold uppercase tracking-widest transition-colors duration-500",
                            compact && "line-clamp-2 text-xs tracking-wider",
                            (isDone || isRunning) ? toneClassName : "text-muted-foreground/50"
                        )
                        }
                    >
                            {meta.label}
                    </span>

                    {totalTargets > 0 && (
                        <div className={cn("absolute bottom-2 grid gap-1", compact ? "inset-x-2.5" : "inset-x-3")}>
                            <span className={cn("text-center font-semibold text-muted-foreground", compact ? "text-[11px]" : "text-sm")}>
                                {processedTargets} / {totalTargets} targets
                                {failedTargets > 0 ? ` · ${failedTargets} failed` : ""}
                            </span>
                            <span className="h-1 overflow-hidden rounded-full bg-white/10">
                                <span className="block h-full rounded-full bg-current transition-[width] duration-500" style={{width: `${targetPercentage}%`}}/>
                            </span>
                        </div>
                    )}
                </div>
                <div className={cn("absolute inset-0 flex items-center justify-center rounded-md border bg-[#102448]/95 px-4 py-3 text-center backdrop-blur-sm [backface-visibility:hidden] [transform:rotateY(180deg)]",
                    borderClassName, compact && "px-2.5 py-2.5"
                )}
                >
                    <p className={cn("leading-snug text-foreground/85", compact ? "line-clamp-[8] text-xs" : "line-clamp-6 text-sm")}>{meta.description}</p>
                </div>
            </div>
        </button>
    );
}

function distributeY(count: number): number[] {
    if (count <= 1) return [50];
    const top = 8;
    const bottom = 92;
    return Array.from({length: count}, (_, i) => top + (i*(bottom - top)) / (count-1));
}

const PILL_CORNER_OFFSET = 6;
const PILL_WIDTH = 72;
const STAGGER_STEP = 6;

function cornerY(y: number): number {
    if(y<50) return y + PILL_CORNER_OFFSET;
    if(y>50) return y - PILL_CORNER_OFFSET;
    return y;
}

function FanColumn({
    sources,
    side,
}: {
    sources: SourceWithPhase[];
    side: "left" | "right";
}) {
    const ys = distributeY(sources.length);
    const hubX = side === "left" ? 100 : 0;
    const baseNearX = side === "left" ? 80: 20;
    const nearXs = sources.map((_, i) => {
        const offset = i % 2 === 1 ? STAGGER_STEP : 0;
        return side === "left" ? baseNearX - offset : baseNearX + offset;
    });

    return (
        <div className="relative h-full min-h-[620px] w-full">
            <svg
                className="pointer-events-none absolute inset-0 h-full w-full"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                aria-hidden="true"
            >
                {sources.map((source, i) => {
                    const lineActive = source.phase === "line" || source.phase === "done";
                    return (
                        <line
                            key={source.source_name}
                            x1={hubX}
                            y1={50}
                            x2={nearXs[i]}
                            y2={cornerY(ys[i])}
                            pathLength={100}
                            strokeDasharray={100}
                            strokeDashoffset={lineActive ? 0 : 100}
                            className= {cn(
                                "transition-[stroke,stroke-dashoffset] duration-[700ms] ease-out",
                                lineActive ? lineToneClassName[source.status]
                                : "stroke-muted-foreground/25"
                            )}
                            strokeWidth={0.4}
                            strokeLinecap="round"
                        />
                    );
                })}
            </svg>
            <span
                aria-hidden="true"
                className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-success ring-4 ring-brand-success/15 shadow-[0_0_10px_2px_rgba(74,222,128,0.55)]"
                style={{left: `${hubX}%`}}
            />
            {sources.map((source,i)=> (
                <div
                    key={source.source_name}
                    className="absolute -translate-y-1/2"
                    style = {{
                        top: `${ys[i]}%`,
                        width: `${PILL_WIDTH}%`,
                        ...(side === "left" ? {right: `${100 - nearXs[i]}%`} : {left: `${nearXs[i]}%`}),
                    }}
                >
                <SourceCard sourceName={source.source_name} status={source.status} phase={source.phase} totalTargets={source.total_targets} completedTargets={source.completed_targets} failedTargets={source.failed_targets}/>
            </div>
            ))}
        </div>
    );
}

function sourcePhase(status: SourceStatus): SourcePhase {
    if(status === "pending") return "idle";
    if(status === "running") return "line";
    return "done";
}

function ScanNetworkDiagram({sources, progress, isComplete}: {sources: RealTimeScanStatus["sources"]; progress: number; isComplete: boolean}) {
    const withPhase: SourceWithPhase[] = sources.map((s)=> ({
        ...s,
        status: s.status as SourceStatus,
        phase: sourcePhase(s.status as SourceStatus),
    }));
    const mid = Math.ceil(withPhase.length / 2);
    const left = withPhase.slice(0,mid);
    const right = withPhase.slice(mid);

    return (
        <div className="hidden flex-col gap-4 lg:flex">
            <div className="origin-top -mb-[62px] scale-90">
                <div className="grid min-h-[620px] grid-cols-[minmax(240px,1fr)_auto_minmax(240px,1fr)] items-stretch">
                    <FanColumn sources = {left} side = "left"/>
                    <div className="flex h-full flex-col items-center justify-center gap-4 px-4">
                        <div className="flex items-center gap-3">
                        <div className="rounded-2xl border border-[#1c2a42] bg-gradient-to-br from-[#0d1e36] to-[#091829] p-4 shadow-[0_4px_20px_rgba(0,8,24,0.5)]">
                                <ScanRadar isComplete={isComplete}/>
                            </div>
                    </div>
                    <div className="flex w-48 flex-col items-center gap-1.5">
                        <Progress
                            value = {progress}
                            className="h-2 bg-muted"
                            indicatorClassName="bg-brand-success transition-[transform] duration-[3500ms] ease-linear"
                        />
                        <span className="text-xs font-semibold text-brand-success"> {progress}%</span>
                    </div>
                    </div>
                    <FanColumn sources={right} side="right"/>
                </div>
            </div>
            </div>
    );
}

function ScanMobileOverview({sources, progress, isComplete}: {sources: RealTimeScanStatus["sources"]; progress: number; isComplete: boolean}) {
    const doneCount = sources.filter((s) => TERMINAL_SOURCE_STATUSES.has(s.status as SourceStatus)).length;

    return (
        <div className="flex flex-col gap-5 lg:hidden">
            <div className="flex flex-col items-center gap-3">
                <div className="rounded-2xl border border-[#1c2a42] bg-gradient-to-br from-[#0d1e36] to-[#091829] p-3 shadow-[0_4px_20px_rgba(0,8,24,0.5)]">
                    <div className="size-[140px]">
                        <div className="origin-top-left scale-[0.54]">
                            <ScanRadar isComplete={isComplete}/>
                        </div>
                    </div>
                </div>
                <div className="flex w-full max-w-xs flex-col items-center gap-1.5">
                    <div className="flex w-full items-center gap-3">
                        <Progress
                            value = {progress}
                            className="h-2 flex-1 bg-muted"
                            indicatorClassName="bg-brand-success transition-[transform] duration-[3500ms] ease-linear"
                        />
                        <span className="text-xs font-semibold text-brand-success">{progress}%</span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                        {doneCount} of {sources.length} sources done
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-2 items-start gap-2.5">
                {sources.map((source) => {
                    const status = source.status as SourceStatus;
                    return (
                        <SourceCard
                            key={source.source_name}
                            compact
                            sourceName={source.source_name}
                            status={status}
                            phase={sourcePhase(status)}
                            totalTargets={source.total_targets}
                            completedTargets={source.completed_targets}
                            failedTargets={source.failed_targets}
                        />
                    );
                })}
            </div>
        </div>
    );
}

export default function ScanProgress() {
    const searchParams = useSearchParams();
    const scanId = searchParams.get("scan_id");
    const [scan, setScan] = useState<RealTimeScanStatus | null>(null);
    const [error, setError] = useState<string | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const poll = useCallback(async (id: string) => {
        try {
            const result = await fetchScanStatus(id);
            setScan(result);
            setError(null);
            const indexFinished =
                result.status === "failed" ||
                result.rag_index_status === "ready" ||
                result.rag_index_status === "failed";
            
            if (
                TERMINAL_SCAN_STATUSES.has(result.status) &&
                indexFinished && pollRef.current
            ) {
                clearInterval(pollRef.current);
                pollRef.current = null;
            }
        }catch (err) {
            setError(err instanceof Error ? err.message : "Unable to load scan status");
        }
    },[]);

    useEffect(()=> {
        if (!scanId) return;
        void poll(scanId);
        pollRef.current = setInterval(()=> void poll(scanId), POLL_INTERVAL_MS);
        return() => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    },[scanId, poll]);
    if(!scanId) {
        return (
            <div className="mx-auto flex w-full max-w-[1700px] flex-col gap-4">
                <p className="text-sm text-muted-foreground">
                    No scan selected. Start a new scan from the {" "}
                    <Link href="/phase2_scan" className="text-brand-cyan hover:underline">
                        Scans
                    </Link>{" "}
                    page.
                </p>
            </div>
        );
    }
    if(error && !scan) {
        return (
            <div className="mx-auto flex w-full max-w-[1700px] flex-col gap-4">
                <p className="text-sm text-brand-alert">{error}</p>
            </div>
        );
    }

    if(!scan) {
        return (
            <div className="mx-auto flex w-full max-w-[1700px] flex-col gap-4">
                <p className="text-sm text-muted-foreground">Loading scan status...</p>
            </div>
        );
    }

    const visibleSources = scan.sources.filter((s)=> s.source_name !== "hunter.io" && s.source_name !== "cpe_resolver");
    return (
        <div className="mx-auto flex w-full max-w-[1700px] flex-col gap-6">
            <nav aria-label = "Breadcrumb" className="flex items-center gap-1 text-sm text-muted-foreground">
                <Link href = "/phase2_scan" className="hover:text-foreground hover:underline">
                    Scans
                </Link>
                <ChevronRight className="size-4"/>
                <span>{scan.domain}</span>
                <ChevronRight className="size-4"/>
                <span className="text-foreground">Progress</span>
            </nav>

            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <div className="flex flex-wrap items-center gap-3">
                        <h1 className="text-2xl font-semibold text-foreground">{scan.domain}</h1>
                        <Badge className="bg-brand-cyan text-black capitalize">{scan.status}</Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                        {scanTypeLabel[scan.scan_type] ?? scan.scan_type} &bull; {scan.progress}% complete
                    </p>
                </div>
                <div className="flex gap-2">
                    <Link href={`/phase2_scan/graph?scan_id=${scan.scan_id}`}>
                        <Button variant="outline" className="gap-2 border-brand-panel-border text-foreground hover:border-brand-cyan hover:text-brand-cyan">
                            View Scan Graph
                        </Button>
                    </Link>
                    {TERMINAL_SCAN_STATUSES.has(scan.status) ? (
                        <Link href = {`/phase2_scan/results/${scan.scan_id}`}>
                            <Button className="gap-2 bg-brand-cyan text-black hover:bg-brand-cyan/85">
                                View Results
                                <ChevronRight className="size-4" />
                            </Button>
                        </Link>
                    ): null}
                </div>
            </div>

            {error && <p className="text-xs text-brand-alert">{error} </p>}
            <ScanDetailsBar scan = {{ ...scan, sources: visibleSources}}/>

            <Card className={cardClassName} >
                <CardContent className="flex flex-col gap-4">
                    <h2 className={sectionTitleClassName}> Overall Progress </h2>
                        <ScanNetworkDiagram sources = {visibleSources} progress={scan.progress} isComplete={TERMINAL_SCAN_STATUSES.has(scan.status)}/>
                        <ScanMobileOverview sources={visibleSources} progress={scan.progress} isComplete={TERMINAL_SCAN_STATUSES.has(scan.status)}/>
                </CardContent>
            </Card>
        </div>
    );
}