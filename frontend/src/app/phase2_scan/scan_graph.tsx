"use client";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
    AlertTriangle,
    Bug,
    ChevronRight,
    Crosshair,
    FileSearch,
    Fingerprint,
    Flame,
    Focus,
    Gauge,
    GitCompare,
    Globe,
    Info,
    Link2,
    Lock,
    Mail,
    Minus,
    Network,
    Plus,
    ShieldAlert,
    ShieldCheck,
    X,
    type LucideIcon,
} from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn, capitalize } from "@/lib/utils";
import {
    fetchScanFindings,
    fetchScanGraph,
    fetchScanGraphCompare,
    fetchScanGraphNeighborhood,
    fetchScanGraphPaths,
    fetchScanGraphSummary,
    fetchScanHistory,
    fetchScanStatus,
    type DashboardFindingItem,
    type GraphCompareResponse,
    type GraphConcentration,
    type GraphEdge,
    type GraphNeighborhoodResponse,
    type GraphNode,
    type GraphPath,
    type GraphSummaryResponse,
    type RealTimeScanStatus,
    type ScanGraphResponse,
    type ScanHistoryItem,
    type ScanSourceStatus,
} from "@/lib/scanService";

const POLL_INTERVAL_MS = 4000;
const TERMINAL_SCAN_STATUSES = new Set(["completed", "failed", "partial"]);
const NEW_NODE_HIGHLIGHT_MS = 3000;

const scanTypeLabel: Record<string, string> = {
    active_vulnerability: "Active Vulnerability Scan",
    passive_ctem: "Passive Reconnaissance",
};

type Severity = "critical" | "high" | "medium" | "low" | "info";

const SEVERITY_ORDER: Record<Severity, number> = {
    info: 0,
    low: 1,
    medium: 2,
    high: 3,
    critical: 4,
};

interface SourceMeta {
    label: string;
    description: string;
    icon: LucideIcon;
}

const SOURCE_META: Record<string, SourceMeta> = {
    dns:{ label: "DNS", description: "Performs DNS enumeration for the target domain.", icon: Network },
    "crt.sh":{ label: "crt.sh", description: "Searches Certificate Transparency logs for issued certificates.", icon: FileSearch },
    urlscan:{ label: "URLScan", description: "Queries urlscan.io for prior scans and page metadata for the domain.", icon: Globe },
    wappalyzer:{ label: "Wappalyzer", description: "Identifies web technologies used by the target.", icon: Fingerprint },
    shodan:{ label: "Shodan", description: "Queries Shodan for exposed devices, banners, and services tied to the target's IP.", icon: Fingerprint },
    hibp:{ label: "HaveIBeenPwned", description: "Checks associated email addresses and domains against known data breach databases.", icon: ShieldAlert },
    target_resolution:{ label: "Resolving Target", description: "Resolves the verified domain into IPv4 and IPv6 addresses.", icon: Globe },
    nmap:{ label: "Discovering ports", description: "Checks whether the host is reachable and discovers open ports and network services.", icon: Crosshair },
    http_security: { label: "Checking HTTP", description: "Inspects HTTP responses and security headers such as CSP and HSTS.", icon: ShieldCheck },
    tls:{ label: "Inspecting TLS", description: "Checks certificates, TLS versions, cipher suites, expiry, issuer and self-signed status.", icon: Lock },
    fingerprint:{ label: "Detecting Tech", description: "Identifies servers, frameworks, languages, CMS platforms, CDNs and their versions.", icon: Fingerprint },
    cve: { label: "Matching CVEs", description: "Cross-references detected products and versions with vulnerability information and generates CVE findings.", icon: Bug },
};

const DEFAULT_SOURCE_META: SourceMeta = {
    label: "unknown source",
    description: "No description available for this source.",
    icon: Info,
};

const sourceStatusConfig: Record<string, { label: string; className: string }> = {
    pending: { label: "Pending", className: "border-muted-foreground/30 text-muted-foreground bg-muted/40" },
    running: { label: "Running", className: "border-brand-cyan text-brand-cyan bg-brand-cyan/10" },
    completed: { label: "Completed", className: "border-brand-success text-brand-success bg-brand-success/10" },
    failed: { label: "Failed", className: "border-brand-alert text-brand-alert bg-brand-alert/10" },
    partial: { label: "Partial", className: "border-brand-yellow text-brand-yellow bg-brand-yellow/10" },
    skipped: { label: "Skipped", className: "border-muted-foreground/30 text-muted-foreground bg-muted/40" },
};

interface Accent {
    text: string;
    border: string;
    iconBg: string;
    strokeMuted: string;
}

const KIND_STYLE: Record<"internet" | "domain" | "ip" | "asset" | "service" | "technology", Accent> = {
    internet: { text: "text-muted-foreground", border: "border-[#2a3f66]", iconBg: "bg-white/5", strokeMuted: "stroke-muted-foreground/60" },
    domain: { text: "text-brand-blue", border: "border-brand-blue/50", iconBg: "bg-brand-blue/10", strokeMuted: "stroke-brand-blue/60" },
    ip: { text: "text-brand-cyan", border: "border-brand-cyan/50", iconBg: "bg-brand-cyan/10", strokeMuted: "stroke-brand-cyan/60" },
    asset: { text: "text-brand-blue", border: "border-brand-blue/50", iconBg: "bg-brand-blue/10", strokeMuted: "stroke-brand-blue/60" },
    service: { text: "text-[#a855f7]", border: "border-[#a855f7]/50", iconBg: "bg-[#a855f7]/10", strokeMuted: "stroke-[#a855f7]/60" },
    technology: { text: "text-brand-success", border: "border-brand-success/50", iconBg: "bg-brand-success/10", strokeMuted: "stroke-brand-success/60" },
};

const SEVERITY_ACCENT: Record<Severity, Accent> = {
    critical: { text: "text-[#ef4444]", border: "border-[#991b1b]", iconBg: "bg-[#991b1b]/10", strokeMuted: "stroke-[#ef4444]/60" },
    high: { text: "text-[#f97316]", border: "border-[#a34908]", iconBg: "bg-[#a34908]/10", strokeMuted: "stroke-[#f97316]/60" },
    medium: { text: "text-[#facc15]", border: "border-[#8a6a00]", iconBg: "bg-[#8a6a00]/10", strokeMuted: "stroke-[#facc15]/60" },
    low: { text: "text-[#60a5fa]", border: "border-[#18549a]", iconBg: "bg-[#18549a]/10", strokeMuted: "stroke-[#60a5fa]/60" },
    info: { text: "text-muted-foreground", border: "border-[#334155]", iconBg: "bg-[#334155]/10", strokeMuted: "stroke-muted-foreground/60" },
};

const SEVERITY_BADGE_CLASS: Record<Severity, string> = {
    critical: "border-[#991b1b] text-[#ef4444] bg-[#991b1b]/[0.08]",
    high: "border-[#a34908] text-[#f97316] bg-[#8a6a04]/[0.08]",
    medium: "border-[#8a6a00] text-[#facc15] bg-[#8a6a00]/[0.08]",
    low: "border-[#18549a] text-[#60a5fa] bg-[#18549a]/[0.08]",
    info: "border-[#334155] text-muted-foreground bg-[#334155]/[0.08]",
};

const CONTEXT_BOX_CLASS = "grid gap-1 rounded-[7px] border border-[#26364e] bg-[#0c1828] p-2.5";
const INTERNET_ID ="__internet__";

function normalizeSeverity(value: string | null): Severity {
    if (value ==="critical" || value === "high" || value === "medium" || value === "low" || value === "info") return value;
    return "info";
}

function nodeVisual(node: GraphNode): Accent & { icon: LucideIcon } {
    if (node.type ==="finding") {
        const accent =SEVERITY_ACCENT[normalizeSeverity(node.risk.severity)];
        return { ...accent, icon: Bug };
    }
    if (node.type=== "technology") return {...KIND_STYLE.technology, icon: Fingerprint };
    if (node.type=== "service") return {...KIND_STYLE.service, icon: Crosshair };
    if (node.type=== "domain") return {...KIND_STYLE.domain, icon: Globe };

    const assetType = typeof node.metadata.asset_type === "string" ? node.metadata.asset_type.toLowerCase() : "";
    if (assetType === "ipv4" || assetType === "ipv6") return { ...KIND_STYLE.ip, icon: Network };
    if (assetType === "email") return { ...KIND_STYLE.asset, icon: Mail };
    return {...KIND_STYLE.asset, icon: Globe };
}

function nodeSublabel(node: GraphNode): string {
    if (node.type === "domain") return "Domain";
    if (node.type === "service") return "Service";
    if (node.type === "technology") return "Technology";
    if (node.type === "finding") return `${capitalize(normalizeSeverity(node.risk.severity))} Finding`;

    const assetType = typeof node.metadata.asset_type === "string" ? node.metadata.asset_type : "";
    if (assetType === "ipv4" || assetType === "ipv6") return "IP Address";
    if (assetType === "subdomain") return "Subdomain";
    if (assetType === "email") return "Email";
    return "Asset";
}

function nodeDescription(node: GraphNode): string {
    switch (node.type) {
        case "domain":
            return "The verified domain this scan targets.";
        case "service":
            return "An open port and running service discovered by the port scan.";
        case "technology":
            return "A technology fingerprinted from the service or asset it runs on.";
        case "asset": {
            const assetType = typeof node.metadata.asset_type === "string" ? node.metadata.asset_type : "";
            if (assetType === "ipv4" || assetType === "ipv6") return "An IP address the domain resolves to.";
            if (assetType === "subdomain") return "A subdomain discovered during reconnaissance.";
            if (assetType === "email") return "An email address associated with this domain.";
            return "An asset discovered during the scan.";
        }
        default:
            return "";
    }
}

interface LayoutColumn {
    key: string;
    nodes: GraphNode[];
}

function buildColumns(graph: ScanGraphResponse | null): LayoutColumn[] {
    if (!graph || graph.nodes.length === 0) return [];

    const domainNode = graph.nodes.find((n) => n.type === "domain");
    if (!domainNode) return [];

    const children = new Map<string, string[]>();
    for (const edge of graph.edges) {
        const list = children.get(edge.source) ?? [];
        list.push(edge.target);
        children.set(edge.source, list);
    }

    const depthById = new Map<string, number>();
    depthById.set(domainNode.id, 1);
    let frontier = [domainNode.id];
    while (frontier.length > 0) {
        const next: string[] = [];
        for (const id of frontier) {
            const depth = depthById.get(id)!;
            for (const childId of children.get(id) ?? []) {
                if (!depthById.has(childId)) {
                    depthById.set(childId, depth + 1);
                    next.push(childId);
                }
            }
        }
        frontier = next;
    }

    const maxDepth = Math.max(...Array.from(depthById.values()), 1);
    const orphanDepth = maxDepth + 1;

    const byDepth = new Map<number, GraphNode[]>();
    for (const node of graph.nodes) {
        const depth = depthById.get(node.id) ?? orphanDepth;
        const list = byDepth.get(depth) ?? [];
        list.push(node);
        byDepth.set(depth, list);
    }

    const columns: LayoutColumn[] = [{ key: INTERNET_ID, nodes: [] }];
    const maxUsedDepth = Math.max(...Array.from(byDepth.keys()));
    for (let depth = 1; depth <= maxUsedDepth; depth += 1) {
        const columnNodes = (byDepth.get(depth) ?? []).slice().sort((a, b) => a.id.localeCompare(b.id));
        if (columnNodes.length > 0) columns.push({ key: `depth-${depth}`, nodes: columnNodes });
    }

    return columns;
}

interface Anchor {
    left: number;
    right: number;
    y: number;
}

function SeverityBadge({ severity }: { severity: Severity }) {
    return (
        <span className={cn("w-fit shrink-0 rounded-[5px] border px-2 py-1 text-[9px] font-bold uppercase", SEVERITY_BADGE_CLASS[severity])}>
            {severity}
        </span>
    );
}

function GraphNodeCard({
    node,
    isSelected,
    isNew,
    isBusy,
    isAddedSinceCompare,
    onSelect,
    registerRef,
}: {
    node: GraphNode;
    isSelected: boolean;
    isNew: boolean;
    isBusy: boolean;
    isAddedSinceCompare: boolean;
    onSelect: (id: string) => void;
    registerRef: (id: string, el: HTMLButtonElement | null) => void;
}) {
    const visual = nodeVisual(node);
    const Icon = visual.icon;

    return (
        <button
            type="button"
            ref={(el) => registerRef(node.id, el)}
            onClick={() => onSelect(node.id)}
            aria-pressed={isSelected}
            title={isBusy ? "The scan is still looking for more here" : undefined}
            className={cn(
                "relative flex w-full items-center gap-2.5 rounded-lg border bg-[#102448]/85 px-3 py-2.5 text-left backdrop-blur-sm transition-[box-shadow,border-color] duration-200",
                visual.border,
                (isNew || isBusy) && "animate-pulse shadow-[0_0_14px_rgba(43,216,245,0.45)]",
                isSelected && "shadow-[0_0_0_1px_currentColor,0_0_18px_rgba(43,216,245,0.25)]",
            )}
        >
            {node.risk.finding_count > 0 && node.type !== "finding" && (
                <span className={cn(
                    "absolute -top-1.5 -right-1.5 flex h-4 min-w-4 items-center justify-center rounded-full border px-1 text-[9px] font-bold",
                    SEVERITY_BADGE_CLASS[normalizeSeverity(node.risk.severity)],
                )}>
                    {node.risk.finding_count}
                </span>
            )}
            {isAddedSinceCompare && (
                <span
                    title="New since the compared scan"
                    className="absolute -top-1.5 -left-1.5 rounded-full border border-brand-success/60 bg-brand-success/15 px-1 py-0.5 text-[8px] font-bold text-brand-success"
                >
                    NEW
                </span>
            )}
            <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-md border", visual.border, visual.iconBg, visual.text)}>
                <Icon className="size-4" />
            </span>
            <span className="min-w-0">
                <span className={cn("block truncate text-[13px] font-semibold", visual.text)}>{node.label}</span>
                <span className="block truncate text-[10px] text-muted-foreground">{nodeSublabel(node)}</span>
            </span>
        </button>
    )
}

function InternetNodeCard({ registerRef }: { registerRef: (id: string, el: HTMLButtonElement | null) => void }) {
    return (
        <button
            type="button"
            ref={(el) => registerRef(INTERNET_ID, el)}
            disabled
            className="flex w-full items-center gap-2.5 rounded-lg border border-[#2a3f66] bg-[#102448]/85 px-3 py-2.5 text-left backdrop-blur-sm"
        >
            <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-[#2a3f66] bg-white/5 text-muted-foreground">
                <Globe className="size-4" />
            </span>
            <span className="min-w-0">
                <span className="block truncate text-[13px] font-semibold text-muted-foreground">Internet</span>
                <span className="block truncate text-[10px] text-muted-foreground">External</span>
            </span>
        </button>
    );
}

function GraphLegend() {
    const nodeLegend: { label: string; className: string }[] = [
        { label: "Domain", className: "bg-brand-blue" },
        { label: "IP Address", className: "bg-brand-cyan" },
        { label: "Asset", className: "bg-brand-blue" },
        { label: "Service", className: "bg-[#a855f7]" },
        { label: "Technology", className: "bg-brand-success" },
        { label: "Finding", className: "bg-brand-alert" },
    ];

    return (
        <div className="flex flex-wrap items-start gap-3">
            <div className="rounded-lg border border-brand-panel-border bg-[#0b1625]/95 p-3.5 text-[11px]">
                <h3 className="mb-2.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Node Legend</h3>
                <ul className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                    {nodeLegend.map((item)=>(
                        <li key={item.label} className="flex items-center gap-2 whitespace-nowrap text-[#cbd5e1]">
                            <span className={cn("size-2.5 shrink-0 rounded-full", item.className)} />
                            {item.label}
                        </li>
                    ))}
                </ul>
            </div>

            <div className="rounded-lg border border-brand-panel-border bg-[#0b1625]/95 p-3.5 text-[11px]">
                <h3 className="mb-2.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Activity</h3>
                <ul className="flex flex-col gap-1.5 text-[#cbd5e1]">
                    <li className="flex items-center gap-2 whitespace-nowrap">
                        <span className="size-2.5 shrink-0 animate-pulse rounded-full bg-brand-cyan" /> Scan still looking here
                    </li>
                    <li className="flex items-center gap-2 whitespace-nowrap"><span className="h-0.5 w-4 bg-brand-cyan" /> Discovered</li>
                    <li className="flex items-center gap-2 whitespace-nowrap"><span className="h-0.5 w-4 animate-pulse bg-brand-cyan" /> Just found</li>
                </ul>
            </div>
        </div>
    )
}

function HotSpotPills({
    concentrations,
    onSelect,
}:{
    concentrations: GraphConcentration[];
    onSelect: (nodeId: string) => void;
}) {
    if (concentrations.length === 0) return null;

    return (
        <div className="flex flex-wrap items-center gap-1.5">
            <span className="flex items-center gap-1 text-[10px] font-semibold tracking-wide text-muted-foreground uppercase">
                <Flame size={12} className="text-brand-alert" /> Hot spots
            </span>
            {concentrations.slice(0, 3).map((c) => (
                <button
                    key={c.node_id}
                    type="button"
                    onClick={() => onSelect(c.node_id)}
                    className="inline-flex items-center gap-1.5 rounded-full border border-brand-panel-border bg-[#0b1625] px-2.5 py-1 text-[10px] text-[#cbd5e1] hover:border-brand-cyan hover:text-brand-cyan"
                >
                    <span className="max-w-[110px] truncate">{c.label}</span>
                    <span className={cn(
                        "shrink-0 rounded-full px-1 text-[9px] font-bold",
                        c.critical_count > 0 ?"text-[#ef4444]":"text-[#f97316]",
                    )}>
                        {c.finding_count}
                    </span>
                </button>
            ))}
        </div>
    )
}
//add tab button style and risk path
function tabButtonClass(active: boolean) {
    return cn(
        "rounded-md px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide transition-colors",
        active ?"bg-brand-cyan/10 text-brand-cyan":"text-muted-foreground hover:text-foreground",
    );
}

function RiskPathsTab({
    scanId,
    node,
    nodesById,
    onSelectFinding,
}: {
    scanId: string;
    node: GraphNode;
    nodesById: Map<string, GraphNode>;
    onSelectFinding:(id: string)=>void;
}) {
    const [paths,setPaths] =useState<GraphPath[] | null>(null);
    const [loading,setLoading] =useState(true);
    const [error,setError]=useState<string | null>(null);

    useEffect(() => {
        //Ignore stale responses scan changes mid fetch
        let cancelled = false;
        setLoading(true);
        setError(null);
        setPaths(null);
        //Scope paths to a specific asset when available
        const params = node.type === "asset" && node.entity_id
            ? { asset_id: node.entity_id, limit: 5 }
            : { limit: 5 };

        fetchScanGraphPaths(scanId, params)
            .then((res) => { if (!cancelled) setPaths(res.paths); })
            .catch((err: unknown) =>{if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load risk paths"); })
            .finally(() => { if (!cancelled) setLoading(false); });

        return ()=> { cancelled = true};
    }, [scanId, node.id, node.type, node.entity_id]);

    if (loading)return <p className="p-3 text-[11px] text-muted-foreground">Loading risk paths...</p>;
    if (error)return <p className="p-3 text-[11px] text-brand-alert">{error}</p>;
    if (!paths || paths.length === 0) return <p className="p-3 text-[11px] text-muted-foreground">No risk paths found here.</p>;

    return (
        <div className="flex flex-col gap-2.5 p-3">
            {paths.map((path) => {
                const findingId = path.nodes[path.nodes.length - 1];
                return (
                    <button
                        key={path.id}
                        type="button"
                        onClick={() => onSelectFinding(findingId)}
                        className="flex flex-col gap-1.5 rounded-lg border border-brand-panel-border bg-[#0f1c30] p-3 text-left hover:bg-[#131f34]"
                    >
                        <div className="flex items-center justify-between gap-2">
                            <SeverityBadge severity={normalizeSeverity(path.risk.severity)} />
                            {path.risk.max_cvss !== null && (
                                <span className="text-[10px] text-muted-foreground">CVSS {path.risk.max_cvss}</span>
                            )}
                        </div>
                        <div className="flex flex-wrap items-center gap-1 text-[10px] text-[#cbd5e1]">
                            {path.nodes.map((nodeId, index) => (
                                <span key={nodeId} className="flex items-center gap-1">
                                    {index > 0 && <ChevronRight className="size-3 text-muted-foreground" />}
                                    <span className="truncate">{nodesById.get(nodeId)?.label ?? nodeId}</span>
                                </span>
                            ))}
                        </div>
                    </button>
                );
            })}
        </div>
    );
}

function DetailsPanel({
    scanId,
    node,
    edges,
    nodesById,
    findingsByEntityId,
    onSelectFinding,
}: {
    scanId: string;
    node: GraphNode;
    edges: GraphEdge[];
    nodesById: Map<string, GraphNode>;
    findingsByEntityId: Map<string, DashboardFindingItem>;
    onSelectFinding: (id: string) => void;
}) {
    const [tab, setTab] = useState<"details" | "findings" | "paths">("details");
    const visual = nodeVisual(node);
    const Icon = visual.icon;

    const findingDetail = node.type === "finding" && node.entity_id ? findingsByEntityId.get(node.entity_id) : undefined;
    const incoming = edges.filter((e)=> e.target === node.id).length;
    const outgoing = edges.filter((e)=> e.source === node.id).length;
    const sourceEdge = edges.find((e)=> e.target === node.id);
    // For the domain node, surface every finding in the scan
    // for other nodes only findin directly linked via AFFECTED_BY.
    const relatedFindings: GraphNode[] = node.type === "domain"
        ? Array.from(nodesById.values()).filter((n)=> n.type === "finding")
        : edges
            .filter((e) => e.source === node.id && e.type === "AFFECTED_BY")
            .map((e) => nodesById.get(e.target))
            .filter((n): n is GraphNode => Boolean(n));

    return (
        <aside className="flex min-w-0 flex-col overflow-hidden rounded-[10px] border border-brand-panel-border bg-[#0b1625]">
            <div className="flex gap-1 border-b border-brand-panel-border p-2">
                <button type="button" onClick={() => setTab("details")} className={tabButtonClass(tab === "details")}>
                    Details
                </button>
                <button type="button" onClick={() => setTab("findings")} className={tabButtonClass(tab === "findings")}>
                    Findings ({relatedFindings.length})
                </button>
                <button type="button" onClick={() => setTab("paths")} className={tabButtonClass(tab === "paths")}>
                    Paths
                </button>
            </div>

            {tab === "details" ? (
                <div className="flex flex-col gap-4 p-4">
                    <div className="flex items-start gap-3">
                        <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg border", visual.border, visual.iconBg, visual.text)}>
                            <Icon className="size-4.5" />
                        </span>
                        <div className="min-w-0">
                            <h2 className="m-0 text-[15px] leading-snug text-foreground">{node.label}</h2>
                            <p className="m-0 mt-0.5 text-[11px] text-muted-foreground">{nodeSublabel(node)}</p>
                        </div>
                    </div>

                    {node.type === "finding" ? (
                        <div className="flex flex-wrap gap-2">
                            <SeverityBadge severity={normalizeSeverity(node.risk.severity)} />
                            {node.risk.max_cvss !== null && (
                                <span className="rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-1 text-[10px] text-[#9eacbd]">
                                    CVSS {node.risk.max_cvss}
                                </span>
                            )}
                            {typeof node.metadata.cve_id === "string" && node.metadata.cve_id && (
                                <span className="rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-1 text-[10px] text-[#9eacbd]">
                                    {node.metadata.cve_id}
                                </span>
                            )}
                        </div>
                    ) : node.risk.finding_count > 0 && (
                        <div className="flex flex-wrap gap-2">
                            <SeverityBadge severity={normalizeSeverity(node.risk.severity)} />
                            <span className="rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-1 text-[10px] text-[#9eacbd]">
                                {node.risk.finding_count} finding{node.risk.finding_count === 1 ? "" : "s"}
                            </span>
                        </div>
                    )}

                    <dl className="m-0 grid grid-cols-2 gap-2.5">
                        <div className={CONTEXT_BOX_CLASS}>
                            <dt className="text-[9px] text-muted-foreground">Discovered via</dt>
                            <dd className="m-0 [overflow-wrap:anywhere] text-[10px] text-[#d1dae6]">
                                {sourceEdge?.provenance.source ?? "Scan target"}
                            </dd>
                        </div>
                        <div className={CONTEXT_BOX_CLASS}>
                            <dt className="text-[9px] text-muted-foreground">Connections</dt>
                            <dd className="m-0 text-[10px] text-[#d1dae6]">{incoming} in &bull; {outgoing} out</dd>
                        </div>
                        {node.type === "service" && (
                            <>
                                <div className={CONTEXT_BOX_CLASS}>
                                    <dt className="text-[9px] text-muted-foreground">Host : Port</dt>
                                    <dd className="m-0 [overflow-wrap:anywhere] text-[10px] text-[#d1dae6]">
                                        {String(node.metadata.host ?? "-")} : {String(node.metadata.port ?? "-")}
                                    </dd>
                                </div>
                                <div className={CONTEXT_BOX_CLASS}>
                                    <dt className="text-[9px] text-muted-foreground">Product</dt>
                                    <dd className="m-0 [overflow-wrap:anywhere] text-[10px] text-[#d1dae6]">
                                        {String(node.metadata.product ?? "Unknown")} {String(node.metadata.version ?? "")}
                                    </dd>
                                </div>
                            </>
                        )}
                        {node.type === "technology" && (
                            <div className={CONTEXT_BOX_CLASS}>
                                <dt className="text-[9px] text-muted-foreground">Detected by</dt>
                                <dd className="m-0 [overflow-wrap:anywhere] text-[10px] text-[#d1dae6]">
                                    {String(node.metadata.detection_source ?? "Unknown")}
                                </dd>
                            </div>
                        )}
                    </dl>

                    <section>
                        <h3 className="m-0 mb-2 text-[11px] uppercase text-muted-foreground">Description</h3>
                        <p className="m-0 text-[11px] leading-relaxed text-[#abb7c7]">
                            {findingDetail?.description ?? nodeDescription(node) ?? "No description available."}
                        </p>
                    </section>

                    {node.type === "finding" && findingDetail?.recommendation && (
                        <section>
                            <h3 className="m-0 mb-2 text-[11px] uppercase text-muted-foreground">Remediation</h3>
                            <p className="m-0 text-[11px] leading-relaxed text-[#abb7c7]">{findingDetail.recommendation}</p>
                        </section>
                    )}
                </div>
            ) : tab === "findings" ? (
                <div className="flex flex-col gap-2.5 p-3">
                    {relatedFindings.length === 0 ? (
                        <p className="p-2 text-[11px] text-muted-foreground">No findings tied to this node yet.</p>
                    ) : (
                        relatedFindings.map((finding) => (
                            <button
                                key={finding.id}
                                type="button"
                                onClick={() => onSelectFinding(finding.id)}
                                className={cn(
                                    "flex flex-col gap-1.5 rounded-lg border bg-[#0f1c30] p-3 text-left hover:bg-[#131f34]",
                                    finding.id === node.id ? "border-brand-cyan" : "border-brand-panel-border",
                                )}
                            >
                                <div className="flex items-center justify-between gap-2">
                                    <span className="text-[12px] font-semibold text-foreground">{finding.label}</span>
                                    <SeverityBadge severity={normalizeSeverity(finding.risk.severity)} />
                                </div>
                                {finding.risk.max_cvss !== null && (
                                    <span className="text-[10px] text-muted-foreground">CVSS {finding.risk.max_cvss}</span>
                                )}
                            </button>
                        ))
                    )}
                </div>
            ) : (
                <RiskPathsTab scanId={scanId} node={node} nodesById={nodesById} onSelectFinding={onSelectFinding} />
            )}
        </aside>
    );
}

function WorkerActivityTable ({ sources }: { sources: ScanSourceStatus[] }) {
    const visibleSources = sources.filter((s) => s.source_name !== "hunter.io");
    
    return(
        <Card className="border border-brand-panel-border bg-brand-panel">
            <CardContent className="flex flex-col gap-4">
            <div>
                <h2 className="m-0 text-sm font-bold tracking-[0.15em] text-foreground/90 uppercase">Live Worker Activity</h2>
                <p className="mt-1 text-[11px] text-muted-foreground">What each scan step is doing right now.</p>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] border-collapse">
                    <thead>
                        <tr>
                            {["Worker", "Description", "Status", "Error"].map((h) => (
                                <th key={h} className="border-b border-brand-panel-border px-3 py-2.5 text-left text-[10px] text-muted-foreground uppercase">{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                            {visibleSources.map((source) => {
                            const meta = SOURCE_META[source.source_name] ?? {...DEFAULT_SOURCE_META, label: source.source_name };
                            const statusInfo = sourceStatusConfig[source.status] ?? sourceStatusConfig.pending;
                            const Icon = meta.icon;
                            return (
                                <tr key={source.source_name} className="hover:bg-[#101e30]">
                                    <td className="border-b border-brand-panel-border/75 px-3 py-3 text-[12px]  text-foreground">
                                        <span className="flex items-center gap-2">
                                            <Icon className="size-3.5 text-brand-cyan"/>
                                            {meta.label}
                                        </span>
                                    </td>
                                    <td className="border-b border-brand-panel-border/75 px-3 py-3 text-[11px] text-muted-foreground">{meta.description}</td>
                                    <td className="border-b border-brand-panel-border/75 px-3 py-3 text-[11px]">
                                        <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase", statusInfo.className)}>
                                            <span className={cn("size-1.5 rounded-full",source.status === "running" ? "animate-pulse bg-brand-cyan" : "bg-current")}/>
                                            {statusInfo.label}
                                        </span>
                                    </td>
                                    <td className="border-b border-brand-panel-border/75 px-3 py-3 text-[11px] text-muted-foreground">
                                        {source.error_message ?? "-"}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
            </CardContent>
        </Card>
    )
}

interface ScanGraphProps {
    scanId?: string;
    variant?: "standalone" | "embedded";
}

export default function ScanGraph({scanId: scanIdProp, variant = "standalone" }: ScanGraphProps = {}){
    const searchParams = useSearchParams();
    const scanId = scanIdProp ?? searchParams.get("scan_id");

    const [scan, setScan] = useState<RealTimeScanStatus | null>(null);
    const [graph, setGraph] = useState<ScanGraphResponse | null>(null);
    const [findings, setFindings] = useState<DashboardFindingItem[]>([]);
    const [summary, setSummary] = useState<GraphSummaryResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [newIds, setNewIds] = useState<Set<string>>(new Set());

    const [focusMode, setFocusMode] = useState(false);
    const [neighborhood, setNeighborhood] = useState<GraphNeighborhoodResponse | null>(null);
    const [neighborhoodLoading, setNeighborhoodLoading] = useState(false);

    const [previousScanId, setPreviousScanId] = useState<string | null>(null);
    const [compare, setCompare] = useState<GraphCompareResponse | null>(null);
    const [compareLoading, setCompareLoading] = useState(false);
    const [compareError, setCompareError] = useState<string | null>(null);
    const [showCompare, setShowCompare] = useState(false);

    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const newIdsTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const prevNodeIdsRef = useRef<Set<string>>(new Set());

    const containerRef = useRef<HTMLDivElement>(null);
    const nodeRefs = useRef(new Map<string, HTMLButtonElement>());
    const [anchors, setAnchors] = useState<Record<string, Anchor>>({});

    const poll = useCallback(async (id: string) => {
        try {
            const [statusResult, graphResult] = await Promise.all([
                fetchScanStatus(id),
                fetchScanGraph(id),
            ])
            setScan(statusResult);
            setGraph(graphResult);
            setError(null);

            if (TERMINAL_SCAN_STATUSES.has(statusResult.status) && pollRef.current) {
                clearInterval(pollRef.current);
                pollRef.current = null;
            }
        } catch (err) {
            setError(err instanceof Error ? err.message:"Unable to load the scan graph");
        }

        fetchScanFindings(id, { limit: 200 }).then(setFindings).catch(()=>{});
        fetchScanGraphSummary(id).then(setSummary).catch(()=>{});
    }, []);

    useEffect(() => {
        if (!scanId) return;
        void poll(scanId);
        pollRef.current = setInterval(() => void poll(scanId), POLL_INTERVAL_MS);
        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
            if (newIdsTimeoutRef.current) clearTimeout(newIdsTimeoutRef.current);
        };
    }, [scanId, poll]);

    useEffect(() => {
        if (!graph) return;
        const currentIds = new Set(graph.nodes.map((n) => n.id));
        const prev = prevNodeIdsRef.current;
        const added = new Set<string>();
        currentIds.forEach((id) => {
            if (!prev.has(id)) added.add(id);
        });
        prevNodeIdsRef.current = currentIds;

        if (added.size > 0 && prev.size > 0) {
            setNewIds(added);
            if (newIdsTimeoutRef.current) clearTimeout(newIdsTimeoutRef.current);
            newIdsTimeoutRef.current = setTimeout(() => setNewIds(new Set()), NEW_NODE_HIGHLIGHT_MS);
        }
    }, [graph]);

    useEffect(() => {
        if (!graph || selectedId) return;
        const findingNodes = graph.nodes.filter((n) => n.type === "finding");
        const best = [...findingNodes].sort(
            (a, b) => SEVERITY_ORDER[normalizeSeverity(b.risk.severity)] - SEVERITY_ORDER[normalizeSeverity(a.risk.severity)],
        )[0];
        const domainNode = graph.nodes.find((n) => n.type === "domain");
        setSelectedId(best?.id ?? domainNode?.id ?? null);
    }, [graph, selectedId]);

    const previousScanLookupDoneRef = useRef(false);
    useEffect(() => {
        if (!scan || previousScanLookupDoneRef.current) return;
        previousScanLookupDoneRef.current = true;

        fetchScanHistory()
            .then((history: ScanHistoryItem[]) => {
                const candidates = history
                    .filter((h) => h.id !== scan.scan_id && h.domain === scan.domain && h.created_at < scan.created_at)
                    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
                if (candidates.length > 0) setPreviousScanId(candidates[0].id);
            })
            .catch(() => {});
    }, [scan]);

    function toggleCompare() {
        if (showCompare) {
            setShowCompare(false);
            return;
        }
        setShowCompare(true);
        if (compare || compareLoading || !scanId || !previousScanId) return;

        setCompareLoading(true);
        setCompareError(null);
        fetchScanGraphCompare(scanId, previousScanId)
            .then(setCompare)
            .catch((err: unknown) => setCompareError(err instanceof Error ? err.message : "Failed to compare scans"))
            .finally(() => setCompareLoading(false));
    }

    function registerRef(id: string, el: HTMLButtonElement | null) {
        if (el) nodeRefs.current.set(id, el);
        else nodeRefs.current.delete(id);
    }

    useLayoutEffect(() => {
        function measure() {
            const container = containerRef.current;
            if (!container) return;
            const containerRect = container.getBoundingClientRect();
            const next: Record<string, Anchor> = {};
            nodeRefs.current.forEach((el, id) => {
                const r = el.getBoundingClientRect();
                next[id] = {
                    left: r.left - containerRect.left,
                    right: r.right - containerRect.left,
                    y: r.top - containerRect.top + r.height / 2,
                };
            });
            setAnchors(next);
        }
        measure();
        const ro = new ResizeObserver(measure);
        if (containerRef.current) ro.observe(containerRef.current);
        window.addEventListener("resize", measure);
        return () => {
            ro.disconnect();
            window.removeEventListener("resize", measure);
        };
    }, [graph]);

    const columns = useMemo(() => buildColumns(graph), [graph]);
    const nodesById = useMemo(() => new Map((graph?.nodes ?? []).map((n) => [n.id, n])), [graph]);
    const findingsByEntityId = useMemo(() => new Map(findings.map((f) => [f.id, f])), [findings]);
    const domainNode = graph?.nodes.find((n) => n.type === "domain");

    const edges = useMemo(() => {
        if (!graph) return [];
        const domainEdge = domainNode ? [{ id: "internet-domain", source: INTERNET_ID, target: domainNode.id, type: "RESOLVES_TO" as const, provenance: { source: "scan", observed_at: null, confidence: 1 } }] : [];
        return [...domainEdge, ...graph.edges];
    }, [graph, domainNode]);

    if (!scanId) {
        return (
            <div className={variant === "standalone" ? "mx-auto flex w-full max-w-[1700px] flex-col gap-4" : "flex min-w-0 flex-col gap-4"}>
                <p className="text-sm text-muted-foreground">
                    No scan selected. Start a new scan from the{" "}
                    <Link href="/phase2_scan" className="text-brand-cyan hover:underline">Scans</Link> page.
                </p>
            </div>
        );
    }

    if (error && !scan) {
        return (
            <div className={variant === "standalone" ? "mx-auto flex w-full max-w-[1700px] flex-col gap-4" : "flex min-w-0 flex-col gap-4"}>
                <p className="text-sm text-brand-alert">{error}</p>
            </div>
        );
    }

    if (!scan) {
        return (
            <div className={variant === "standalone" ? "mx-auto flex w-full max-w-[1700px] flex-col gap-4" : "flex min-w-0 flex-col gap-4"}>
                <p className="text-sm text-muted-foreground">Loading scan graph...</p>
            </div>
        );
    }

    const selectedNode = (selectedId && nodesById.get(selectedId)) || domainNode;
    const assetsDiscovered = summary
        ? summary.counts.assets + summary.counts.services + summary.counts.technologies
        : graph?.nodes.filter((n) => n.type === "asset" || n.type === "service" || n.type === "technology").length ?? 0;
    const findingsTotal = summary?.counts.findings ?? domainNode?.risk.finding_count ?? 0;
    const criticalCount = summary?.risk.critical_findings
        ?? graph?.nodes.filter((n) => n.type === "finding" && n.risk.severity === "critical").length ?? 0;
    const isRunning = !TERMINAL_SCAN_STATUSES.has(scan.status);

    const addedNodeIds = showCompare && compare ? new Set(compare.added_nodes) : null;

    // A node with no children yet may just not have been reached by the scan
    // yet - pulse it while the scan is still running so it reads as "waiting",
    // not stalled. Finding/technology nodes are always leaves, so they never
    // qualify, even mid-scan.
    const childCounts = new Map<string, number>();
    for (const edge of edges) {
        childCounts.set(edge.source, (childCounts.get(edge.source) ?? 0) + 1);
    }
    function isNodeBusy(node: GraphNode): boolean {
        if (!isRunning) return false;
        if (node.type !== "domain" && node.type !== "asset" && node.type !== "service") return false;
        return (childCounts.get(node.id) ?? 0) === 0;
    }

    const statChips = [
        { icon: Network, value: assetsDiscovered, label: "Assets Discovered", accent: KIND_STYLE.ip },
        { icon: Bug, value: findingsTotal, label: "Findings", accent: SEVERITY_ACCENT.high },
        { icon: AlertTriangle, value: criticalCount, label: "Critical", accent: SEVERITY_ACCENT.critical },
        { icon: Gauge, value: `${scan.progress}%`, label: "Scan Progress", accent: KIND_STYLE.technology },
    ];

    const compareChips = compare ? [
        { icon: Plus, value: compare.added_nodes.length, label: "New nodes", accent: "text-brand-success" },
        { icon: Minus, value: compare.removed_nodes.length, label: "Removed", accent: "text-brand-alert" },
        { icon: GitCompare, value: compare.changed_nodes.length, label: "Changed", accent: "text-brand-cyan" },
        { icon: Link2, value: compare.added_edges.length, label: "New links", accent: "text-brand-cyan" },
    ] : [];

    const graphCard = (
        <Card className="border border-brand-panel-border bg-brand-panel">
            <CardContent className="flex flex-col gap-4">
                <div>
                    <h2 className="m-0 text-sm font-bold tracking-[0.15em] text-foreground/90 uppercase">Live Scan Graph</h2>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                        Builds up as the active scan discovers assets, services and findings. Click a node for details.
                    </p>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-brand-panel-border bg-[#0b1625]/60 px-3 py-2">
                    <div className="flex items-center gap-1">
                        {previousScanId && (
                            <button
                                type="button"
                                onClick={toggleCompare}
                                className={cn(
                                    "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[11px] font-semibold uppercase tracking-wide",
                                    showCompare ? "bg-brand-success/10 text-brand-success" : "text-muted-foreground hover:bg-white/5 hover:text-foreground",
                                )}
                            >
                                <GitCompare size={13} />
                                Compare
                            </button>
                        )}
                    </div>

                    {summary && <HotSpotPills concentrations={summary.concentrations} onSelect={setSelectedId} />}
                </div>

                {showCompare && (
                    <div className="rounded-lg border border-brand-panel-border bg-[#0b1625]/95 p-3.5">
                        <div className="mb-2.5 flex items-center justify-between">
                            <h3 className="m-0 text-[10px] font-semibold tracking-wide text-muted-foreground uppercase">Compared to previous scan</h3>
                            <button type="button" onClick={() => setShowCompare(false)} aria-label="Close comparison" className="text-muted-foreground hover:text-foreground">
                                <X size={14} />
                            </button>
                        </div>

                         {compareLoading ? (
                            <p className="m-0 text-[11px] text-muted-foreground">Comparing against the previous scan...</p>
                        ) : compareError ? (
                            <p className="m-0 text-[11px] text-brand-alert">{compareError}</p>
                        ) : compare ? (
                            <div className="flex flex-col gap-3">
                                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                                    {compareChips.map((chip) => (
                                        <div key={chip.label} className="flex items-center gap-2 rounded-md border border-brand-panel-border bg-[#0f1c30] px-2.5 py-2">
                                            <chip.icon size={14} className={chip.accent} />
                                            <div className="flex flex-col leading-tight">
                                                <strong className="text-[13px] text-foreground">{chip.value}</strong>
                                                <span className="text-[9px] tracking-wide text-muted-foreground uppercase">{chip.label}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                {("critical_findings" in compare.risk_change || "high_findings" in compare.risk_change) && (
                                    <div className="flex flex-wrap gap-x-5 gap-y-1 text-[11px]">
                                        {"critical_findings" in compare.risk_change && (
                                            <span className="text-[#ef4444]">
                                                Critical {String(compare.risk_change.critical_findings.previous)} &rarr; {String(compare.risk_change.critical_findings.current)}
                                            </span>
                                        )}
                                        {"high_findings" in compare.risk_change && (
                                            <span className="text-[#f97316]">
                                                High {String(compare.risk_change.high_findings.previous)} &rarr; {String(compare.risk_change.high_findings.current)}
                                            </span>
                                        )}
                                    </div>
                                )}
                            </div>
                        ) : null}
                    </div>
                )}

                {columns.length <= 2 ? (
                    <div className="flex min-h-[220px] flex-col items-center justify-center rounded-[0.8rem] border border-dashed border-brand-panel-border bg-[rgba(16,24,39,0.55)] p-8 text-center text-muted-foreground">
                        <Globe size={28} className="mb-2 text-brand-cyan" />
                        <h3 className="m-0 text-[0.95rem] text-foreground">
                            {isRunning ? "Waiting for the scan to discover assets" : "No graph data was recorded for this scan"}
                        </h3>
                        <p className="mt-1.5 mb-0 text-[0.78rem]">
                            {isRunning ? "The graph fills in as domain resolution, port scanning, and CVE matching complete." : "Nothing was discovered before the scan finished."}
                        </p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <div ref={containerRef} className="relative" style={{ minWidth: `${Math.max(columns.length * 180, 720)}px` }}>
                            <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
                                {edges.map((edge) => {
                                    const p = anchors[edge.source];
                                    const c = anchors[edge.target];
                                    if (!p || !c) return null;
                                    const targetNode = nodesById.get(edge.target);
                                    const isNew = newIds.has(edge.target);
                                    const accent = targetNode ? nodeVisual(targetNode) : KIND_STYLE.domain;
                                    const midX = (p.right + c.left) / 2;
                                    const d = `M ${p.right} ${p.y} C ${midX} ${p.y}, ${midX} ${c.y}, ${c.left} ${c.y}`;
                                    return (
                                        <path
                                            key={edge.id}
                                            d={d}
                                            fill="none"
                                            strokeWidth={1.5}
                                            strokeLinecap="round"
                                            className={isNew ? "stroke-brand-cyan animate-pulse" : accent.strokeMuted}
                                        />
                                    );
                                })}
                            </svg>

}



