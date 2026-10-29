"use client";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
    AlertTriangle,
    Bug,
    CheckCircle2,
    ChevronRight,
    Clock,
    Crosshair,
    FileSearch,
    Fingerprint,
    Flame,
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
    fetchScanGraphSummary,
    fetchScanHistory,
    fetchScanStatus,
    type DashboardFindingItem,
    type GraphCompareResponse,
    type GraphConcentration,
    type GraphEdge,
    type GraphNode,
    type GraphSummaryResponse,
    type RealTimeScanStatus,
    type ScanGraphResponse,
    type ScanHistoryItem,
    type ScanSourceStatus,
} from "@/lib/scanService";
import SidePanelShell from "@/shared/components/SidePanelShell";

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
            if (assetType === "ipv4" || assetType === "ipv6") return "An IP address a scanned hostname resolves to.";
            if (assetType === "subdomain") return "A subdomain discovered during reconnaissance.";
            if (assetType === "email") return "An email address associated with this domain.";
            return "An asset discovered during the scan.";
        }
        default:
            return "";
    }
}

const ROW_STAGES = ["target_resolution", "nmap", "http_security", "tls", "fingerprint", "cve"] as const;
type RowStageKey = typeof ROW_STAGES[number];
const DOMAIN_WIDE_SOURCES = ["dns", "crt.sh", "shodan", "hibp"];
const SETTLED_SOURCE_STATUSES = new Set(["completed", "partial", "skipped"]);

type StageState = "done" | "running" | "failed" | "pending";
interface RowStage { key: RowStageKey; state: StageState }

interface GraphRow {
    id: string;
    root: GraphNode;
    isApex: boolean;
    nodeIds: Set<string>;
    edges: GraphEdge[];
    discoveredAt: string;
}

function assetKind(node: GraphNode): string {
    return node.type === "asset" ? String(node.metadata.asset_type ?? "").toLowerCase() : "";
}
const isSubdomainNode = (node: GraphNode) => assetKind(node) === "subdomain";
const isIpNode = (node: GraphNode) => ["ip", "ipv4", "ipv6"].includes(assetKind(node));

function buildRows(graph: ScanGraphResponse | null): GraphRow[] {
    if (!graph) return [];
    const domainNode = graph.nodes.find((n) => n.type === "domain");
    if (!domainNode) return [];

    const nodesById = new Map(graph.nodes.map((n) => [n.id, n]));
    const children = new Map<string, string[]>();
    for (const edge of graph.edges) {
        const list = children.get(edge.source) ?? [];
        list.push(edge.target);
        children.set(edge.source, list);
    }

    const collect = (rootId: string, stopAtSubdomains: boolean) => {
        const seen = new Set([rootId]);
        const stack = [rootId];
        while (stack.length > 0) {
            const id = stack.pop()!;
            for (const childId of children.get(id) ?? []) {
                const child = nodesById.get(childId);
                if (!child || seen.has(childId)) continue;
                if (stopAtSubdomains && isSubdomainNode(child)) continue;
                seen.add(childId);
                stack.push(childId);
            }
        }
        return seen;
    };

    const discoveredAt = new Map(
        graph.edges.filter((e) => e.type === "DISCOVERED").map((e) => [e.target, e.provenance.observed_at ?? ""]),
    );
    const subdomainRows = graph.nodes.filter(isSubdomainNode).map((node) => ({
        id: node.id,
        root: node,
        isApex: false,
        nodeIds: collect(node.id, false),
        discoveredAt: discoveredAt.get(node.id) ?? "",
    }));

    const apexIds = collect(domainNode.id, true);
    const placed = new Set(apexIds);
    subdomainRows.forEach((row) => row.nodeIds.forEach((id) => placed.add(id)));
    graph.nodes.forEach((node) => { if (!placed.has(node.id)) apexIds.add(node.id); });

    return [
        { id: domainNode.id, root: domainNode, isApex: true, nodeIds: apexIds, discoveredAt: "" },
        ...subdomainRows,
    ].map((row) => ({ ...row, edges: graph.edges.filter((e) => row.nodeIds.has(e.source) && row.nodeIds.has(e.target)) }));
}

function rowRiskScore(row: GraphRow, nodesById: Map<string, GraphNode>): number {
    const weights = [1, 3, 8, 20, 40];
    let score = 0;
    row.nodeIds.forEach((id) => {
        const node = nodesById.get(id);
        if (node?.type === "finding") score += weights[SEVERITY_ORDER[normalizeSeverity(node.risk.severity)]];
    });
    return score;
}

function rowStages(
    row: GraphRow,
    nodesById: Map<string, GraphNode>,
    sourcesByName: Map<string, ScanSourceStatus>,
    scanRunning: boolean,
): RowStage[] {
    const nodes = [...row.nodeIds].map((id) => nodesById.get(id)).filter((n): n is GraphNode => Boolean(n));
    const findingSources = new Set(row.edges.filter((e) => e.type === "AFFECTED_BY").map((e) => e.provenance.source));
    const evidence: Record<RowStageKey, boolean> = {
        target_resolution: nodes.some(isIpNode),
        nmap: nodes.some((n) => n.type === "service"),
        http_security: findingSources.has("http_security") || findingSources.has("https_security"),
        tls: findingSources.has("tls"),
        fingerprint: nodes.some((n) => n.type === "technology"),
        cve: findingSources.has("cve"),
    };
    const lastEvidence = Math.max(-1, ...ROW_STAGES.map((key, i) => (evidence[key] ? i : -1)));

    return ROW_STAGES.filter((key) => sourcesByName.has(key)).map((key) => {
        const source = sourcesByName.get(key)!;
        if (ROW_STAGES.indexOf(key) <= lastEvidence) return { key, state: "done" };
        if (source.status === "failed") return { key, state: "failed" };
        if (SETTLED_SOURCE_STATUSES.has(source.status)) return { key, state: "done" };
        if (source.status === "running" && scanRunning) return { key, state: "running" };
        return { key, state: "pending" };
    });
}

const STAGE_SEGMENT_CLASS: Record<StageState, string> = {
    done: "bg-brand-success",
    running: "bg-brand-yellow animate-pulse",
    failed: "bg-brand-alert",
    pending: "bg-[#22324d]",
};

const ROW_GRID_CLASS =
    "grid grid-cols-[210px_220px_minmax(0,1fr)] gap-x-10 max-md:grid-cols-[220px_minmax(0,1fr)]";
const ROW_MIN_WIDTH_CLASS = "w-full min-w-[960px] max-md:min-w-[700px]";
const WIDE_HEADER_CLASS = "hidden min-[1280px]:grid";

type RowColumnKey = "host" | "finding" | "technology";
const COLUMN_TITLE: Record<RowColumnKey, string> = {
    host: "Hosts & ports",
    finding: "Findings",
    technology: "Technology",
};
const STAGE_COLUMN: Record<RowStageKey, RowColumnKey> = {
    target_resolution: "host",
    nmap: "host",
    http_security: "finding",
    tls: "finding",
    fingerprint: "technology",
    cve: "finding",
};
const SEVERITIES_DESC: Severity[] = ["critical", "high", "medium", "low", "info"];
const SEVERITY_SHORT: Record<Severity, string> = { critical: "Critical", high: "High", medium: "Medium", low: "Low", info: "Info" };
const SEVERITY_STRIPE_CLASS: Record<Severity, string> = {
    critical: "border-l-[#ef4444]",
    high: "border-l-[#f97316]",
    medium: "border-l-[#facc15]",
    low: "border-l-[#60a5fa]",
    info: "border-l-[#64748b]",
};
const GHOST_ID = "__ghost__";

interface HostView {
    id: string;
    node: GraphNode | null;
    label: string;
    services: GraphNode[];
}
interface TechView {
    id: string;
    label: string;
    nodeIds: string[];
    hostIds: string[];
    tags: string;
    findingCount: number;
}
type FindingCategoryKey = "breach" | "cve" | "tls" | "http" | "dns" | "other";
const FINDING_CATEGORY: Record<FindingCategoryKey, { label: string; short: string; icon: LucideIcon }> = {
    breach: { label: "Data breaches", short: "Breaches", icon: ShieldAlert },
    cve: { label: "Known vulnerabilities (CVEs)", short: "CVEs", icon: Bug },
    tls: { label: "TLS & certificates", short: "TLS", icon: Lock },
    http: { label: "HTTP security headers", short: "Headers", icon: ShieldCheck },
    dns: { label: "DNS & email", short: "DNS & email", icon: Mail },
    other: { label: "Other", short: "Other", icon: AlertTriangle },
};
const CATEGORY_FOR_SOURCE: Record<string, FindingCategoryKey> = {
    http_security: "http",
    https_security: "http",
    tls: "tls",
    cve: "cve",
    hibp: "breach",
    dns: "dns",
};

interface MergedFinding {
    key: string;
    title: string;
    severity: Severity;
    nodeIds: string[];
    hostIds: string[];
    serviceIds: string[];
    techIds: string[];
    origins: string[];
    maxCvss: number | null;
}
interface FindingCategoryGroup {
    id: string;
    key: FindingCategoryKey;
    label: string;
    icon: LucideIcon;
    worst: Severity;
    total: number;
    counts: { severity: Severity; count: number }[];
    items: MergedFinding[];
    hostIds: string[];
    preview: string;
}

function categoryPreview(items: MergedFinding[]): string {
    const titles = items.map((i) => i.title);
    const allMissing = titles.length > 1 && titles.every((t) => /^missing\s/i.test(t));
    const shown = titles.slice(0, 3).map((t) => (allMissing ? t.replace(/^missing\s+/i, "") : t));
    const more = titles.length > 3 ? ` +${titles.length - 3}` : "";
    return `${allMissing ? "Missing: " : ""}${shown.join(" · ")}${more}`;
}

function servicePort(service: GraphNode): string {
    const port = service.metadata.port;
    return port === undefined || port === null ? service.label : `:${String(port)}`;
}
function serviceName(service: GraphNode): string {
    const [name] = service.label.split(" :");
    return name ?? "";
}

function buildRowView(row: GraphRow, nodesById: Map<string, GraphNode>, findingSources: Map<string, string>) {
    const parentOf = (id: string, types?: string[]) => row.edges
        .filter((e) => e.target === id && (!types || types.includes(e.type)))
        .map((e) => e.source);

    const hosts = new Map<string, HostView>();
    row.nodeIds.forEach((id) => {
        const node = nodesById.get(id);
        if (!node || id === row.root.id || ["service", "technology", "finding"].includes(node.type)) return;
        hosts.set(id, { id, node, label: node.label, services: [] });
    });
    const rootHostId = `${row.root.id}:host`;
    const hostForService = new Map<string, string>();
    row.nodeIds.forEach((id) => {
        const node = nodesById.get(id);
        if (node?.type !== "service") return;
        const parent = parentOf(id, ["EXPOSES"]).find((p) => hosts.has(p));
        const hostId = parent ?? rootHostId;
        if (!hosts.has(hostId)) hosts.set(hostId, { id: hostId, node: null, label: row.root.label, services: [] });
        hosts.get(hostId)!.services.push(node);
        hostForService.set(id, hostId);
    });
    hosts.forEach((h) => h.services.sort((a, b) => Number(a.metadata.port ?? 0) - Number(b.metadata.port ?? 0)));
    const hostOf = (id: string) => (hosts.has(id) ? id : hostForService.get(id) ?? null);

    const techs = new Map<string, TechView & { ports: Set<string> }>();
    row.nodeIds.forEach((id) => {
        const node = nodesById.get(id);
        if (node?.type !== "technology") return;
        const entry = techs.get(node.label) ?? { id: `tech:${row.id}:${node.label}`, label: node.label, nodeIds: [], hostIds: [], tags: "", findingCount: 0, ports: new Set<string>() };
        entry.nodeIds.push(id);
        parentOf(id, ["RUNS"]).forEach((parentId) => {
            const parent = nodesById.get(parentId);
            if (parent?.type === "service") entry.ports.add(servicePort(parent));
            const hostId = hostOf(parentId);
            if (hostId && !entry.hostIds.includes(hostId)) entry.hostIds.push(hostId);
        });
        techs.set(node.label, entry);
    });
    const techViews: TechView[] = [...techs.values()].map(({ ports, ...t }) => {
        const portList = [...ports].sort((a, b) => Number(a.slice(1)) - Number(b.slice(1)));
        const hostsPart = t.hostIds.length > 1 ? `${t.hostIds.length} hosts` : "";
        return { ...t, tags: [portList.join(" · "), hostsPart].filter(Boolean).join(" · "), findingCount: 0 };
    }).sort((a, b) => a.label.localeCompare(b.label));

    const allServices = [...hosts.values()].flatMap((h) => h.services);
    const portNumber = (svc: GraphNode) => Number(svc.metadata.port);
    const byPortOrName = (port: number, names: string[]) => {
        const byPort = allServices.filter((svc) => portNumber(svc) === port);
        return byPort.length > 0 ? byPort : allServices.filter((svc) => names.includes(serviceName(svc).toLowerCase()));
    };
    const inferServices = (source: string): GraphNode[] => {
        if (source === "http_security") return byPortOrName(80, ["http"]);
        if (source === "https_security") return byPortOrName(443, ["https", "ssl/http"]);
        if (source === "tls") {
            const tlsEnabled = allServices.filter((svc) => svc.metadata.tls_enabled === true);
            return tlsEnabled.length > 0 ? tlsEnabled : byPortOrName(443, ["https"]);
        }
        return [];
    };
    const techProduct = (label: string) => label.replace(/\s+v?\d[\w.\-]*$/i, "").trim().toLowerCase();
    const matchTechs = (node: GraphNode): TechView[] => {
        const haystack = `${node.label} ${String(node.metadata.cve_id ?? "")} ${String(node.metadata.product ?? "")}`.toLowerCase();
        return techViews.filter((t) => {
            const product = techProduct(t.label);
            const firstWord = product.split(/[\s/]+/)[0];
            return (product.length > 2 && haystack.includes(product)) || (firstWord.length > 3 && haystack.includes(firstWord));
        });
    };

    const rootOrigin = row.isApex ? "Domain-wide" : "Subdomain";
    const merged = new Map<FindingCategoryKey, Map<string, MergedFinding>>();
    row.nodeIds.forEach((id) => {
        const node = nodesById.get(id);
        if (node?.type !== "finding") return;
        const parentEdges = row.edges.filter((e) => e.target === id && e.type === "AFFECTED_BY");
        const source = parentEdges[0]?.provenance.source || (node.entity_id ? findingSources.get(node.entity_id) : undefined) || "";
        const category: FindingCategoryKey = typeof node.metadata.cve_id === "string" && node.metadata.cve_id
            ? "cve" : CATEGORY_FOR_SOURCE[source] ?? "other";
        const severity = normalizeSeverity(node.risk.severity);
        const key = `${severity}|${node.label}`;
        const group = merged.get(category) ?? new Map<string, MergedFinding>();
        const entry = group.get(key) ?? { key, title: node.label, severity, nodeIds: [], hostIds: [], serviceIds: [], techIds: [], origins: [], maxCvss: null };
        entry.nodeIds.push(id);
        const addService = (svc: GraphNode) => {
            if (!entry.serviceIds.includes(svc.id)) entry.serviceIds.push(svc.id);
            const hostId = hostOf(svc.id);
            if (hostId && !entry.hostIds.includes(hostId)) entry.hostIds.push(hostId);
        };
        if (category === "cve") {
            matchTechs(node).forEach((t) => { if (!entry.techIds.includes(t.id)) entry.techIds.push(t.id); });
        }
        if (node.risk.max_cvss !== null && (entry.maxCvss === null || node.risk.max_cvss > entry.maxCvss)) entry.maxCvss = node.risk.max_cvss;
        const parents = parentEdges.map((e) => e.source);
        const inferred = parents.every((p) => p === row.root.id) ? inferServices(source) : [];
        inferred.forEach(addService);
        if (parents.length === 0 && inferred.length === 0 && !entry.origins.includes(rootOrigin)) entry.origins.push(rootOrigin);
        inferred.forEach((svc) => {
            const origin = `${servicePort(svc)} ${serviceName(svc)}`.trim();
            if (!entry.origins.includes(origin)) entry.origins.push(origin);
        });
        parents.forEach((parentId) => {
            const parentNode = nodesById.get(parentId);
            if (parentNode?.type === "service") addService(parentNode);
            if (parentId === row.root.id && inferred.length > 0) return;
            const hostId = hostOf(parentId);
            if (hostId && !entry.hostIds.includes(hostId)) entry.hostIds.push(hostId);
            const parent = nodesById.get(parentId);
            const origin = parentId === row.root.id || !parent ? rootOrigin
                : parent.type === "service" ? `${servicePort(parent)} ${serviceName(parent)}`.trim()
                : parent.label;
            if (!entry.origins.includes(origin)) entry.origins.push(origin);
        });
        group.set(key, entry);
        merged.set(category, group);
    });
    const categories: FindingCategoryGroup[] = [...merged.entries()].map(([key, group]) => {
        const items = [...group.values()].sort((a, b) =>
            SEVERITY_ORDER[b.severity] - SEVERITY_ORDER[a.severity] || b.nodeIds.length - a.nodeIds.length || a.title.localeCompare(b.title));
        const counts = SEVERITIES_DESC
            .map((severity) => ({ severity, count: items.filter((i) => i.severity === severity).reduce((n, i) => n + i.nodeIds.length, 0) }))
            .filter((c) => c.count > 0);
        return {
            id: `category:${row.id}:${key}`,
            key,
            label: FINDING_CATEGORY[key].label,
            icon: FINDING_CATEGORY[key].icon,
            worst: counts[0].severity,
            total: counts.reduce((n, c) => n + c.count, 0),
            counts,
            items,
            hostIds: [...new Set(items.flatMap((i) => i.hostIds))],
            preview: categoryPreview(items),
        };
    }).sort((a, b) => SEVERITY_ORDER[b.worst] - SEVERITY_ORDER[a.worst] || b.total - a.total);

    categories.forEach((c) => c.items.forEach((item) => item.techIds.forEach((techId) => {
        const tech = techViews.find((t) => t.id === techId);
        if (tech) tech.findingCount += item.nodeIds.length;
    })));

    const severityTotals = SEVERITIES_DESC
        .map((severity) => ({ severity, total: categories.reduce((n, c) => n + (c.counts.find((x) => x.severity === severity)?.count ?? 0), 0) }))
        .filter((t) => t.total > 0);

    return { hosts: [...hosts.values()].sort((a, b) => a.label.localeCompare(b.label)), hostOf, techViews, categories, severityTotals };
}

function RowStatusCard({
    row,
    stages,
    sources,
    scanRunning,
    severityTotals,
    collapsed,
    onToggleCollapsed,
}: {
    row: GraphRow;
    stages: RowStage[];
    sources: ScanSourceStatus[];
    scanRunning: boolean;
    severityTotals: { severity: Severity; total: number }[];
    collapsed: boolean;
    onToggleCollapsed: () => void;
}) {
    const running = stages.find((s) => s.state === "running");
    const settled = stages.every((s) => s.state === "done" || s.state === "failed") || !scanRunning;
    const failedCount = stages.filter((s) => s.state === "failed").length;
    const runningMeta = running ? SOURCE_META[running.key] : null;
    const RunningIcon = runningMeta?.icon;
    const domainWide = row.isApex ? sources.filter((s) => DOMAIN_WIDE_SOURCES.includes(s.source_name)) : [];

    return (
        <div className={cn(
            "flex flex-col gap-2.5 rounded-lg border bg-[#0f1c30] p-3.5 transition-[border-color,box-shadow] duration-500",
            running ? "border-brand-yellow/70 shadow-[0_0_10px_1px_rgba(255,200,66,0.2)]"
                : settled && stages.length > 0 ? "border-brand-success/40" : "border-brand-panel-border",
        )}>
            <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                    <p className="m-0 text-sm font-semibold break-all text-foreground">{row.root.label}</p>
                    {row.isApex && <p className="m-0 mt-0.5 text-[10px] tracking-wide text-brand-cyan/80 uppercase">Root domain · domain-wide</p>}
                </div>
                <button
                    type="button"
                    onClick={onToggleCollapsed}
                    aria-expanded={!collapsed}
                    aria-label={collapsed ? `Show graph for ${row.root.label}` : `Hide graph for ${row.root.label}`}
                    className="grid size-6 shrink-0 place-items-center rounded-md text-muted-foreground hover:bg-white/5 hover:text-foreground"
                >
                    <ChevronRight className={cn("size-4 transition-transform", !collapsed && "rotate-90")} />
                </button>
            </div>

            {stages.length > 0 && !settled && (
                <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${stages.length}, minmax(0, 1fr))` }}>
                    {stages.map((stage) => (
                        <span
                            key={stage.key}
                            title={`${SOURCE_META[stage.key]?.label ?? stage.key}: ${stage.state}`}
                            className={cn("h-1.5 rounded-full transition-colors duration-500", STAGE_SEGMENT_CLASS[stage.state])}
                        />
                    ))}
                </div>
            )}

            {stages.length > 0 && (
                <p className="m-0 flex items-center gap-1.5 text-xs font-semibold">
                    {runningMeta && RunningIcon ? (
                        <>
                            <RunningIcon className="size-3.5 shrink-0 animate-pulse text-brand-yellow" />
                            <span className="text-brand-yellow">{runningMeta.label}</span>
                        </>
                    ) : settled ? (
                        <>
                            <CheckCircle2 className={cn("size-3.5 shrink-0", failedCount ? "text-brand-alert" : "text-brand-success")} />
                            <span className={failedCount ? "text-brand-alert" : "text-brand-success"}>
                                {failedCount ? `Complete · ${failedCount} step${failedCount === 1 ? "" : "s"} failed` : "Complete"}
                            </span>
                        </>
                    ) : (
                        <>
                            <Clock className="size-3.5 shrink-0 text-[#94a3b8]" />
                            <span className="text-[#94a3b8]">Queued</span>
                        </>
                    )}
                </p>
            )}

            {severityTotals.length > 0 ? (
                <div className="flex flex-wrap gap-1">
                    {severityTotals.map((b) => (
                        <span key={b.severity} className={cn("rounded-[5px] border px-1.5 py-0.5 text-[10px] font-bold", SEVERITY_BADGE_CLASS[b.severity])}>
                            {b.total} {SEVERITY_SHORT[b.severity]}
                        </span>
                    ))}
                </div>
            ) : settled ? (
                <p className="m-0 text-[11px] text-[#94a3b8]">No findings</p>
            ) : null}

            {domainWide.length > 0 && (
                <div className="flex flex-wrap gap-1.5 border-t border-brand-panel-border pt-2.5">
                    {domainWide.map((source) => {
                        const meta = SOURCE_META[source.source_name] ?? { ...DEFAULT_SOURCE_META, label: source.source_name };
                        const Icon = meta.icon;
                        const tone = source.status === "running" ? "border-brand-yellow/60 text-brand-yellow"
                            : source.status === "failed" ? "border-brand-alert/50 text-brand-alert"
                            : SETTLED_SOURCE_STATUSES.has(source.status) ? "border-brand-success/40 text-brand-success"
                            : "border-brand-panel-border text-[#94a3b8]";
                        return (
                            <span key={source.source_name} title={`${meta.label}: ${source.status}`}
                                className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold", tone)}>
                                <Icon className={cn("size-3", source.status === "running" && "animate-pulse")} />
                                {meta.label}
                            </span>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

function RowsHeader() {
    return (
        <div className={cn(WIDE_HEADER_CLASS, ROW_GRID_CLASS, "sticky top-0 z-10 border-b border-brand-panel-border bg-brand-panel/95 px-[13px] py-2 backdrop-blur")}>
            {["Subdomain", COLUMN_TITLE.host, COLUMN_TITLE.finding].map((title) => (
                <span key={title} className="text-[11px] font-semibold tracking-[0.12em] text-[#cbd5e1] uppercase">{title}</span>
            ))}
        </div>
    );
}

function SubdomainRow({
    row,
    stages,
    sources,
    scanRunning,
    nodesById,
    selectedId,
    newIds,
    addedNodeIds,
    collapsed,
    flash,
    onToggleCollapsed,
    onSelect,
    onOpenFinding,
    findingSources,
}: {
    row: GraphRow;
    stages: RowStage[];
    sources: ScanSourceStatus[];
    scanRunning: boolean;
    nodesById: Map<string, GraphNode>;
    selectedId: string | null;
    newIds: Set<string>;
    addedNodeIds: Set<string> | null;
    collapsed: boolean;
    flash: boolean;
    onToggleCollapsed: () => void;
    onSelect: (id: string) => void;
    onOpenFinding: (rowId: string, category: FindingCategoryKey, itemKey: string) => void;
    findingSources: Map<string, string>;
}) {
    const containerRef = useRef<HTMLDivElement>(null);
    const nodeRefs = useRef(new Map<string, HTMLElement>());
    const [anchors, setAnchors] = useState<Record<string, Anchor>>({});
    const [hoverFocus, setHoverFocus] = useState<{ ids: string[]; downstream: boolean } | null>(null);
    const { hosts, hostOf, techViews, categories, severityTotals } = buildRowView(row, nodesById, findingSources);
    const [categoryFilter, setCategoryFilter] = useState<FindingCategoryKey | "all">("all");
    const findingsScrollRef = useRef<HTMLDivElement>(null);
    const [findingsScroll, setFindingsScroll] = useState({ overflow: false, atStart: true, atEnd: true });

    const findingsBlockId = `findings:${row.id}`;
    const activeFilter = categoryFilter !== "all" && categories.length > 1 && categories.some((c) => c.key === categoryFilter) ? categoryFilter : "all";
    const findingChips = categories
        .filter((c) => activeFilter === "all" || c.key === activeFilter)
        .flatMap((c) => c.items.map((item) => ({ item, category: c })))
        .sort((a, b) =>
            SEVERITY_ORDER[b.item.severity] - SEVERITY_ORDER[a.item.severity]
            || b.item.nodeIds.length - a.item.nodeIds.length
            || a.item.title.localeCompare(b.item.title));
    const totalFindings = severityTotals.reduce((n, t) => n + t.total, 0);
    const findingRows = findingChips.length <= 2 ? 1 : findingChips.length <= 4 ? 2 : 3;
    const findingCols = Math.max(1, Math.ceil(findingChips.length / findingRows));
    const CHIP_WIDTH = 230, CHIP_GAP = 8, PANEL_CHROME = 30;
    const findingsPanelWidth = Math.max(260, findingCols * CHIP_WIDTH + (findingCols - 1) * CHIP_GAP + PANEL_CHROME);
    const showCategoryFilter = categories.length > 1 && totalFindings >= 5;

    const links: { id: string; source: string; target: string; accent: Accent; drawn: boolean; dashed?: boolean }[] = [];
    const serviceHost = new Map<string, string>();
    hosts.forEach((h) => {
        links.push({ id: `${row.id}->${h.id}`, source: row.root.id, target: h.id, accent: h.node ? nodeVisual(h.node) : KIND_STYLE.ip, drawn: true });
        h.services.forEach((svc) => {
            serviceHost.set(svc.id, h.id);
            links.push({ id: `${h.id}->${svc.id}`, source: h.id, target: svc.id, accent: KIND_STYLE.service, drawn: false });
        });
    });
    const chipId = (categoryKey: FindingCategoryKey, itemKey: string) => `fchip:${row.id}:${categoryKey}|${itemKey}`;
    const allChipIds: string[] = [];
    const cveTechIds = new Set<string>();
    categories.forEach((c) => c.items.forEach((item) => {
        const id = chipId(c.key, item.key);
        allChipIds.push(id);
        const accent = SEVERITY_ACCENT[item.severity];
        const upstream = item.serviceIds.length > 0 ? item.serviceIds : item.hostIds.length > 0 ? item.hostIds : [row.root.id];
        upstream.forEach((src) => links.push({ id: `${src}->${id}`, source: src, target: id, accent, drawn: false }));
        item.techIds.forEach((techId) => {
            cveTechIds.add(techId);
            links.push({ id: `${id}->${techId}`, source: id, target: techId, accent, drawn: false });
        });
    }));
    if (categories.length > 0) {
        const accent = SEVERITY_ACCENT[severityTotals[0].severity];
        const inSources = hosts.length > 0 ? hosts.map((h) => h.id) : [row.root.id];
        inSources.forEach((src) => links.push({ id: `${src}->${findingsBlockId}`, source: src, target: findingsBlockId, accent, drawn: true }));
        techViews.forEach((t) => links.push({
            id: `${findingsBlockId}->${t.id}`, source: findingsBlockId, target: t.id,
            accent: cveTechIds.has(t.id) ? SEVERITY_ACCENT.high : KIND_STYLE.technology, drawn: true, dashed: !cveTechIds.has(t.id),
        }));
    } else {
        techViews.forEach((t) => (t.hostIds.length > 0 ? t.hostIds : hosts.map((h) => h.id)).forEach((hostId) =>
            links.push({ id: `${hostId}=>${t.id}`, source: hostId, target: t.id, accent: KIND_STYLE.technology, drawn: true, dashed: true })));
    }
    const findingsPerService = new Map<string, number>();
    categories.forEach((c) => c.items.forEach((item) => item.serviceIds.forEach((svcId) =>
        findingsPerService.set(svcId, (findingsPerService.get(svcId) ?? 0) + 1))));

    const nextStage = scanRunning ? stages.find((s) => s.state === "running" || s.state === "pending") : undefined;
    const columnCount: Record<RowColumnKey, number> = { host: hosts.length, finding: totalFindings, technology: techViews.length };
    const ghostColumn = nextStage && columnCount[STAGE_COLUMN[nextStage.key]] === 0 ? STAGE_COLUMN[nextStage.key] : null;
    if (ghostColumn === "host" || (ghostColumn === "finding" && hosts.length === 0)) {
        links.push({ id: `${row.id}:ghost`, source: row.root.id, target: GHOST_ID, accent: KIND_STYLE.internet, drawn: true });
    } else if (ghostColumn === "finding") {
        links.push({ id: `${row.id}:ghost`, source: hosts[0].id, target: GHOST_ID, accent: KIND_STYLE.internet, drawn: true });
    }
    const portsPending = Boolean(scanRunning && stages.find((s) => s.key === "nmap" && s.state !== "done" && s.state !== "failed"));

    function relatedTo(focus: string[], includeDownstream: boolean): Set<string> {
        const related = new Set(focus);
        const walk = (from: string[], forward: boolean) => {
            const stack = [...from];
            while (stack.length > 0) {
                const id = stack.pop()!;
                for (const link of links) {
                    const next = forward ? (link.source === id ? link.target : null) : (link.target === id ? link.source : null);
                    if (next && !related.has(next)) { related.add(next); stack.push(next); }
                }
            }
        };
        walk(focus, false);
        if (includeDownstream) walk(focus, true);
        return related;
    }
    const selectedFocus = ((): { ids: string[]; downstream: boolean } | null => {
        if (!selectedId || !row.nodeIds.has(selectedId)) return null;
        if (serviceHost.has(selectedId)) return { ids: [selectedId], downstream: true };
        const host = hostOf(selectedId);
        if (host) return { ids: [host], downstream: false };
        const tech = techViews.find((t) => t.nodeIds.includes(selectedId));
        if (tech) return { ids: [tech.id], downstream: false };
        for (const c of categories) {
            const item = c.items.find((i) => i.nodeIds.includes(selectedId));
            if (item) return { ids: [chipId(c.key, item.key)], downstream: true };
        }
        return null;
    })();
    const hovered = hoverFocus ? relatedTo(hoverFocus.ids, hoverFocus.downstream) : null;
    const highlighted = hovered ?? (selectedFocus ? relatedTo(selectedFocus.ids, selectedFocus.downstream) : null);
    const anyChipLit = () => allChipIds.some((id) => highlighted?.has(id));
    const isLinkLit = (link: { source: string; target: string }) => {
        if (!highlighted) return false;
        if (link.target === findingsBlockId) return highlighted.has(link.source) && anyChipLit();
        if (link.source === findingsBlockId) return highlighted.has(link.target) && anyChipLit();
        return highlighted.has(link.source) && highlighted.has(link.target);
    };
    const dimmed = (id: string) => Boolean(hovered && !hovered.has(id));
    const hoverProps = (ids: string[], downstream = true) => ({
        onMouseEnter: () => setHoverFocus({ ids, downstream }),
        onMouseLeave: () => setHoverFocus(null),
        onFocus: () => setHoverFocus({ ids, downstream }),
        onBlur: () => setHoverFocus(null),
    });

    const layoutKey = `${[...row.nodeIds].sort().join("|")}::${ghostColumn ?? ""}::${collapsed}::${activeFilter}::${findingsPanelWidth}`;
    const measureRef = useRef<() => void>(() => {});
    useLayoutEffect(() => {
        function measure() {
            const container = containerRef.current;
            if (!container) return;
            const containerRect = container.getBoundingClientRect();
            const scrollerRect = findingsScrollRef.current?.getBoundingClientRect();
            const next: Record<string, Anchor> = {};
            nodeRefs.current.forEach((el, id) => {
                const r = el.getBoundingClientRect();
                if (r.width === 0) return;
                if (id.startsWith("fchip:") && scrollerRect && (r.right > scrollerRect.right + 1 || r.left < scrollerRect.left - 1)) return;
                const anchorY = id === findingsBlockId ? Math.min(r.height / 2, 60) : Math.min(r.height / 2, 22);
                next[id] = { left: r.left - containerRect.left, right: r.right - containerRect.left, y: r.top - containerRect.top + anchorY };
            });
            setAnchors(next);
            const scroller = findingsScrollRef.current;
            if (scroller) {
                setFindingsScroll({
                    overflow: scroller.scrollWidth > scroller.clientWidth + 2,
                    atStart: scroller.scrollLeft <= 1,
                    atEnd: scroller.scrollLeft + scroller.clientWidth >= scroller.scrollWidth - 2,
                });
            }
        }
        measureRef.current = measure;
        measure();
        const ro = new ResizeObserver(measure);
        if (containerRef.current) ro.observe(containerRef.current);
        return () => ro.disconnect();
    }, [layoutKey, findingsBlockId]);

    function registerRef(id: string, el: HTMLElement | null) {
        if (el) nodeRefs.current.set(id, el);
        else nodeRefs.current.delete(id);
    }

    const card = (
        <RowStatusCard row={row} stages={stages} sources={sources} scanRunning={scanRunning}
            severityTotals={severityTotals} collapsed={collapsed} onToggleCollapsed={onToggleCollapsed} />
    );
    const ghostStageMeta = nextStage ? SOURCE_META[nextStage.key] : null;
    const serviceCount = hosts.reduce((n, h) => n + h.services.length, 0);
    const isNewOrAdded = (id: string) => newIds.has(id);
    const compareNew = (id: string) => addedNodeIds?.has(id) ?? false;

    const ghost = ghostColumn && nextStage && ghostStageMeta ? (
        <div
            ref={(el) => registerRef(GHOST_ID, el)}
            className={cn(
                "flex items-center gap-2 rounded-lg border border-dashed px-3 py-2.5 text-[11px]",
                nextStage.state === "running" ? "border-brand-yellow/60 text-brand-yellow" : "border-[#2e4466] text-[#94a3b8]",
            )}
        >
            <ghostStageMeta.icon className={cn("size-3.5 shrink-0", nextStage.state === "running" && "animate-pulse")} />
            {nextStage.state === "running" ? `${ghostStageMeta.label}…` : `Waiting for ${ghostStageMeta.label.toLowerCase()}`}
        </div>
    ) : null;

    return (
        <div
            id={`graph-row-${row.id}`}
            className={cn(
                "scroll-mt-24 rounded-xl border p-3 transition-[box-shadow] duration-500",
                row.isApex ? "border-brand-cyan/25 bg-brand-cyan/[0.03]" : "border-brand-panel-border bg-[#0b1625]/60",
                flash && "shadow-[0_0_0_2px_rgba(43,216,245,0.8),0_0_24px_rgba(43,216,245,0.35)]",
            )}
        >
            <div className="md:hidden">{card}</div>

            {collapsed ? (
                <div className="flex items-start gap-10 max-md:mt-2">
                    <div className="w-[210px] shrink-0 max-md:hidden">{card}</div>
                    <button
                        type="button"
                        onClick={onToggleCollapsed}
                        className="mt-1 text-left text-[11px] text-[#94a3b8] hover:text-brand-cyan md:mt-3.5"
                    >
                        Graph hidden · {hosts.length} host{hosts.length === 1 ? "" : "s"} · {serviceCount} port{serviceCount === 1 ? "" : "s"} · {techViews.length} technolog{techViews.length === 1 ? "y" : "ies"} — <span className="text-brand-cyan">Show graph</span>
                    </button>
                </div>
            ) : (
                <div className="overflow-x-auto max-md:mt-3">
                    <div ref={containerRef} className={cn("relative items-start", ROW_GRID_CLASS, ROW_MIN_WIDTH_CLASS)}>
                        <svg className="pointer-events-none absolute inset-0 h-full w-full overflow-visible" aria-hidden="true">
                            {links.filter((l) => l.drawn).map((link) => {
                                const p = anchors[link.source];
                                const c = anchors[link.target];
                                const hostAnchor = serviceHost.has(link.source) ? anchors[serviceHost.get(link.source)!] : undefined;
                                const startX = hostAnchor ? hostAnchor.right : p?.right;
                                if (!p || !c || startX === undefined || startX > c.left) return null;
                                const isGhost = link.target === GHOST_ID;
                                const isLit = isLinkLit(link);
                                const midX = (startX + c.left) / 2;
                                return (
                                    <path
                                        key={link.id}
                                        d={`M ${startX} ${p.y} C ${midX} ${p.y}, ${midX} ${c.y}, ${c.left} ${c.y}`}
                                        fill="none"
                                        strokeWidth={isLit ? 2 : 1.5}
                                        strokeLinecap="round"
                                        strokeDasharray={isGhost || link.dashed ? "4 4" : undefined}
                                        className={cn(
                                            "transition-opacity duration-200",
                                            isGhost ? "stroke-muted-foreground/40" : newIds.has(link.target) ? "stroke-brand-cyan animate-pulse" : link.accent.strokeMuted,
                                            isLit ? "opacity-100" : hovered ? "opacity-10" : "opacity-45",
                                        )}
                                    />
                                );
                            })}
                        </svg>

                        <div ref={(el) => registerRef(row.root.id, el)} className="max-md:hidden">{card}</div>

                        {(() => { const renderColumn = (key: RowColumnKey) => (
                            <div key={key} className="flex min-w-0 flex-col gap-2.5">
                                <span className={cn(
                                    "text-[10px] font-semibold tracking-[0.12em] text-[#94a3b8] uppercase",
                                    key !== "technology" && "min-[1280px]:hidden",
                                )}>{COLUMN_TITLE[key]}</span>

                                {key === "host" && hosts.map((host) => {
                                    const visual = host.node ? nodeVisual(host.node) : { ...KIND_STYLE.asset, icon: Globe };
                                    const Icon = visual.icon;
                                    const hostSelected = selectedId === host.id || host.services.some((s) => s.id === selectedId);
                                    return (
                                        <div
                                            key={host.id}
                                            ref={(el) => registerRef(host.id, el)}
                                            {...hoverProps([host.id])}
                                            className={cn(
                                                "rounded-lg border bg-[#102448]/85 p-2.5 transition-[opacity,box-shadow] duration-200",
                                                visual.border,
                                                dimmed(host.id) && "opacity-35",
                                                hostSelected && "shadow-[0_0_0_1px_rgba(43,216,245,0.7)]",
                                                isNewOrAdded(host.id) && "animate-pulse shadow-[0_0_14px_rgba(43,216,245,0.45)]",
                                            )}
                                        >
                                            <button
                                                type="button"
                                                onClick={() => host.node && onSelect(host.id)}
                                                disabled={!host.node}
                                                className="flex w-full items-center gap-2 text-left disabled:cursor-default"
                                            >
                                                <Icon className={cn("size-4 shrink-0", visual.text)} />
                                                <span className={cn("min-w-0 flex-1 truncate text-[12px] font-semibold", visual.text)} title={host.label}>{host.label}</span>
                                                {compareNew(host.id) && <span className="rounded-full border border-brand-success/60 px-1 text-[8px] font-bold text-brand-success">NEW</span>}
                                            </button>
                                            {host.services.length > 0 ? (
                                                <div className="mt-2 flex flex-wrap gap-1">
                                                    {host.services.map((service) => {
                                                        const count = findingsPerService.get(service.id) ?? 0;
                                                        return (
                                                            <button
                                                                key={service.id}
                                                                type="button"
                                                                ref={(el) => registerRef(service.id, el)}
                                                                onClick={() => onSelect(service.id)}
                                                                onMouseEnter={() => setHoverFocus({ ids: [service.id], downstream: true })}
                                                                onMouseLeave={() => setHoverFocus({ ids: [host.id], downstream: true })}
                                                                onFocus={() => setHoverFocus({ ids: [service.id], downstream: true })}
                                                                onBlur={() => setHoverFocus(null)}
                                                                title={`${service.label}${service.metadata.product ? ` · ${String(service.metadata.product)}` : ""}${count ? ` · ${count} finding${count === 1 ? "" : "s"}` : ""}`}
                                                                className={cn(
                                                                    "inline-flex items-center gap-1 rounded-md border border-[#a855f7]/45 bg-[#a855f7]/10 px-1.5 py-0.5 text-[10px] font-semibold text-[#d8b4fe] transition-opacity hover:border-[#a855f7]",
                                                                    selectedId === service.id && "border-brand-cyan text-brand-cyan",
                                                                    (newIds.has(service.id) || compareNew(service.id)) && "animate-pulse border-brand-cyan",
                                                                    dimmed(service.id) && "opacity-40",
                                                                )}
                                                            >
                                                                {servicePort(service)}
                                                                <span className="font-normal text-[#c4b5fd]/80">{serviceName(service)}</span>
                                                                {count > 0 && <span className="rounded-full bg-white/10 px-1 font-bold text-[#e9d5ff]">{count}</span>}
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                            ) : host.node && isIpNode(host.node) ? (
                                                <p className={cn("m-0 mt-1.5 text-[10px]", portsPending ? "text-brand-yellow" : "text-[#94a3b8]")}>
                                                    {portsPending ? "Scanning ports…" : "No open ports"}
                                                </p>
                                            ) : null}
                                        </div>
                                    );
                                })}

                                {key === "finding" && categories.length > 0 && (
                                    <div
                                        ref={(el) => registerRef(findingsBlockId, el)}
                                        className={cn(
                                            "relative mt-2 flex min-w-0 flex-col gap-2 rounded-xl border border-[#2a3b57] bg-[#0b1625]/50 px-3 pt-4 pb-3 transition-[box-shadow,border-color] duration-300",
                                            highlighted && anyChipLit() && "border-brand-cyan/40 shadow-[0_0_0_1px_rgba(43,216,245,0.15)]",
                                            allChipIds.length > 0 && categories.some((c) => c.items.some((i) => i.nodeIds.some((nodeId) => newIds.has(nodeId)))) && "border-brand-cyan/50",
                                        )}
                                    >
                                        <span className="absolute -top-2.5 left-3 rounded-full border border-[#2a3b57] bg-[#0d1a2c] px-2 py-px text-[10px] font-semibold tracking-wide text-[#cbd5e1] uppercase">
                                            Findings · {totalFindings}{findingsScroll.overflow ? " · scroll for more" : ""}
                                        </span>
                                        {showCategoryFilter && (
                                            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter findings">
                                                {[{ key: "all" as const, label: "All", count: totalFindings, icon: null as LucideIcon | null },
                                                  ...categories.map((c) => ({ key: c.key, label: FINDING_CATEGORY[c.key].short, count: c.total, icon: c.icon }))]
                                                    .map(({ key: filterKey, label, count, icon: FilterIcon }) => (
                                                        <button
                                                            key={filterKey}
                                                            type="button"
                                                            onClick={() => setCategoryFilter(filterKey)}
                                                            aria-pressed={activeFilter === filterKey}
                                                            className={cn(
                                                                "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold",
                                                                activeFilter === filterKey
                                                                    ? "border-brand-cyan/60 bg-brand-cyan/10 text-brand-cyan"
                                                                    : "border-brand-panel-border text-[#94a3b8] hover:text-foreground",
                                                            )}
                                                        >
                                                            {FilterIcon && <FilterIcon className="size-3" />}
                                                            {label} <span className="opacity-70">{count}</span>
                                                        </button>
                                                    ))}
                                            </div>
                                        )}

                                        <div className="relative">
                                        {findingsScroll.overflow && !findingsScroll.atStart && (
                                            <button
                                                type="button"
                                                aria-label="Show previous findings"
                                                onClick={() => findingsScrollRef.current?.scrollBy({ left: -(CHIP_WIDTH + CHIP_GAP), behavior: "smooth" })}
                                                className="absolute top-1/2 left-0 z-10 grid size-7 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-[#2a3b57] bg-[#0d1a2c] text-[#cbd5e1] shadow-[0_2px_8px_rgba(0,0,0,0.5)] hover:border-brand-cyan hover:text-brand-cyan"
                                            >
                                                <ChevronRight className="size-4 rotate-180" />
                                            </button>
                                        )}
                                        {findingsScroll.overflow && !findingsScroll.atEnd && (
                                            <button
                                                type="button"
                                                aria-label="Show more findings"
                                                onClick={() => findingsScrollRef.current?.scrollBy({ left: CHIP_WIDTH + CHIP_GAP, behavior: "smooth" })}
                                                className="absolute top-1/2 right-0 z-10 grid size-7 translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-[#2a3b57] bg-[#0d1a2c] text-[#cbd5e1] shadow-[0_2px_8px_rgba(0,0,0,0.5)] hover:border-brand-cyan hover:text-brand-cyan"
                                            >
                                                <ChevronRight className="size-4" />
                                            </button>
                                        )}
                                        <div
                                            ref={(el) => { findingsScrollRef.current = el; }}
                                            onScroll={(e) => {
                                                const el = e.currentTarget;
                                                const atStart = el.scrollLeft <= 1;
                                                const atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 2;
                                                setFindingsScroll((prev) => (prev.atEnd === atEnd && prev.atStart === atStart ? prev : { ...prev, atStart, atEnd }));
                                                measureRef.current();
                                            }}
                                            className={cn(
                                                "overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
                                                findingsScroll.overflow && !findingsScroll.atStart && !findingsScroll.atEnd && "[mask-image:linear-gradient(to_right,transparent,black_48px,black_calc(100%-48px),transparent)]",
                                                findingsScroll.overflow && findingsScroll.atStart && !findingsScroll.atEnd && "[mask-image:linear-gradient(to_right,black_calc(100%-48px),transparent)]",
                                                findingsScroll.overflow && !findingsScroll.atStart && findingsScroll.atEnd && "[mask-image:linear-gradient(to_right,transparent,black_48px)]",
                                            )}
                                        >
                                            <div
                                                className="grid w-max grid-flow-col auto-cols-[230px] gap-2"
                                                style={{ gridTemplateRows: `repeat(${findingRows}, auto)` }}
                                            >
                                                {findingChips.map(({ item, category }) => {
                                                    const CategoryIcon = category.icon;
                                                    const itemSelected = Boolean(selectedId && item.nodeIds.includes(selectedId));
                                                    const id = chipId(category.key, item.key);
                                                    const ports = [...new Set(item.serviceIds.map((svcId) => {
                                                        const svc = nodesById.get(svcId);
                                                        return svc ? servicePort(svc) : "";
                                                    }).filter(Boolean))].sort((x, y) => Number(x.slice(1)) - Number(y.slice(1)));
                                                    return (
                                                        <button
                                                            key={`${category.key}|${item.key}`}
                                                            type="button"
                                                            ref={(el) => registerRef(id, el)}
                                                            onClick={() => onOpenFinding(row.id, category.key, item.key)}
                                                            {...hoverProps([id], true)}
                                                            aria-haspopup="dialog"
                                                            title={item.title}
                                                            className={cn(
                                                                "flex h-[60px] w-full flex-col justify-between rounded-md border border-l-[3px] border-[#22324d] bg-[#0f1c30] px-2.5 py-1.5 text-left transition-colors hover:bg-[#13233b]",
                                                                SEVERITY_STRIPE_CLASS[item.severity],
                                                                itemSelected && "border-brand-cyan bg-brand-cyan/[0.06]",
                                                                item.nodeIds.some((nodeId) => newIds.has(nodeId)) && "animate-pulse",
                                                                dimmed(id) && "opacity-35",
                                                            )}
                                                        >
                                                            <span className="line-clamp-2 text-[11px] leading-snug text-foreground">{item.title}</span>
                                                            <span className="flex items-center gap-1.5 text-[10px]">
                                                                <CategoryIcon className="size-3 shrink-0 text-[#94a3b8]" aria-label={category.label} />
                                                                <span className={cn("font-semibold", SEVERITY_ACCENT[item.severity].text)}>{SEVERITY_SHORT[item.severity]}</span>
                                                                {ports.length > 0 && <span className="text-[#c4b5fd]">{ports.join(" ")}</span>}
                                                                {item.nodeIds.length > 1 && (
                                                                    <span className="rounded-full bg-white/5 px-1.5 font-bold text-[#94a3b8]">×{item.nodeIds.length}</span>
                                                                )}
                                                            </span>
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                        </div>
                                    </div>
                                )}

                                {key === "technology" && techViews.map((tech) => {
                                    const techSelected = Boolean(selectedId && tech.nodeIds.includes(selectedId));
                                    return (
                                        <button
                                            key={tech.id}
                                            type="button"
                                            ref={(el) => registerRef(tech.id, el)}
                                            onClick={() => onSelect(tech.nodeIds[0])}
                                            {...hoverProps([tech.id])}
                                            title={tech.label}
                                            className={cn(
                                                "flex w-full flex-col gap-0.5 rounded-lg border border-brand-success/45 bg-[#102448]/85 px-2.5 py-2 text-left transition-[opacity,box-shadow] duration-200",
                                                dimmed(tech.id) && "opacity-35",
                                                techSelected && "shadow-[0_0_0_1px_rgba(43,216,245,0.7)]",
                                                tech.nodeIds.some((id) => newIds.has(id)) && "animate-pulse shadow-[0_0_14px_rgba(43,216,245,0.45)]",
                                            )}
                                        >
                                            <span className="flex items-center gap-2">
                                                <Fingerprint className="size-4 shrink-0 text-brand-success" />
                                                <span className="min-w-0 flex-1 truncate text-[12px] font-semibold text-brand-success">{tech.label}</span>
                                                {tech.nodeIds.some(compareNew) && <span className="rounded-full border border-brand-success/60 px-1 text-[8px] font-bold text-brand-success">NEW</span>}
                                            </span>
                                            {tech.findingCount > 0 && (
                                                <span className="ml-6 inline-flex w-fit items-center gap-1 rounded-[5px] border border-[#a34908] bg-[#a34908]/10 px-1.5 py-px text-[10px] font-bold text-[#f97316]">
                                                    <AlertTriangle className="size-3" /> {tech.findingCount} CVE{tech.findingCount === 1 ? "" : "s"}
                                                </span>
                                            )}
                                            {tech.tags && <span className="pl-6 text-[10px] text-[#94a3b8]">on {tech.tags}</span>}
                                        </button>
                                    );
                                })}

                                {key === ghostColumn && ghost}
                            </div>
                        );
                        const showFindingColumn = totalFindings > 0 || ghostColumn === "finding";
                        const showTechColumn = techViews.length > 0 || ghostColumn === "technology";
                        return (
                            <>
                                {renderColumn("host")}
                                <div className="flex min-w-0 items-start gap-x-10">
                                    {showFindingColumn && (
                                        <div
                                            className="min-w-[260px] shrink grow-0 transition-[flex-basis] duration-300 ease-out"
                                            style={{ flexBasis: totalFindings > 0 ? `${findingsPanelWidth}px` : "230px" }}
                                            onTransitionEnd={() => measureRef.current()}
                                        >
                                            {renderColumn("finding")}
                                        </div>
                                    )}
                                    {showTechColumn && <div className="w-[190px] flex-none">{renderColumn("technology")}</div>}
                                </div>
                            </>
                        );
                        })()}
                    </div>
                </div>
            )}
        </div>
    );
}

function FindingsPanel({
    rowLabel,
    category,
    focusItemKey,
    nodesById,
    findingsByEntityId,
    selectedId,
    onShowOnGraph,
    onClose,
}: {
    rowLabel: string;
    category: FindingCategoryGroup;
    focusItemKey: string | null;
    nodesById: Map<string, GraphNode>;
    findingsByEntityId: Map<string, DashboardFindingItem>;
    selectedId: string | null;
    onShowOnGraph: (nodeId: string) => void;
    onClose: () => void;
}) {
    const focusedItem = focusItemKey ? category.items.find((i) => i.key === focusItemKey) : undefined;
    const items = focusedItem ? [focusedItem] : category.items;

    const Icon = category.icon;
    const accent = SEVERITY_ACCENT[category.worst];

    return (
        <SidePanelShell labelledBy="findings-panel-title" onClose={onClose}>
                <header className="flex items-start justify-between gap-3 border-b border-brand-panel-border p-4">
                    <div className="flex min-w-0 items-start gap-3">
                        <span className={cn("grid size-9 shrink-0 place-items-center rounded-lg border", focusedItem ? SEVERITY_ACCENT[focusedItem.severity].border : accent.border, focusedItem ? SEVERITY_ACCENT[focusedItem.severity].iconBg : accent.iconBg, focusedItem ? SEVERITY_ACCENT[focusedItem.severity].text : accent.text)}>
                            <Icon className="size-4.5" />
                        </span>
                        <div className="min-w-0">
                            <h2 id="findings-panel-title" className="m-0 text-base leading-snug font-semibold tracking-normal! text-foreground [font-family:inherit]!">
                                {focusedItem ? focusedItem.title : category.label}
                            </h2>
                            <p className="m-0 mt-0.5 text-[11px] break-all text-[#94a3b8]">
                                {focusedItem
                                    ? `${category.label} · ${rowLabel}`
                                    : `${rowLabel} · ${category.total} finding${category.total === 1 ? "" : "s"}`}
                            </p>
                            <div className="mt-2 flex flex-wrap items-center gap-1.5">
                                {focusedItem ? (
                                    <>
                                        <SeverityBadge severity={focusedItem.severity} />
                                        {focusedItem.maxCvss !== null && (
                                            <span className="rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-0.5 text-[10px] text-[#9eacbd]">CVSS {focusedItem.maxCvss}</span>
                                        )}
                                        {focusedItem.nodeIds.length > 1 && (
                                            <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] font-bold text-[#94a3b8]">×{focusedItem.nodeIds.length}</span>
                                        )}
                                    </>
                                ) : category.counts.map(({ severity, count }) => (
                                    <span key={severity} className={cn("rounded-[5px] border px-1.5 py-px text-[10px] font-bold", SEVERITY_BADGE_CLASS[severity])}>
                                        {count} {SEVERITY_SHORT[severity]}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>
                    <button type="button" onClick={onClose} aria-label="Close findings"
                        className="grid size-8 shrink-0 place-items-center rounded-lg text-[#94a3b8] hover:bg-white/5 hover:text-foreground">
                        <X className="size-4" />
                    </button>
                </header>

                <div className="flex min-h-0 flex-col gap-3 overflow-y-auto overscroll-contain p-4">
                    {items.map((item) => {
                        const single = Boolean(focusedItem);
                        const node = nodesById.get(item.nodeIds[0]);
                        const detail = node?.entity_id ? findingsByEntityId.get(node.entity_id) : undefined;
                        const isSelected = Boolean(selectedId && item.nodeIds.includes(selectedId));
                        return (
                            <article
                                key={item.key}
                                className={cn(
                                    "rounded-lg border border-l-[3px] border-[#22324d] bg-[#0f1c30]",
                                    SEVERITY_STRIPE_CLASS[item.severity],
                                    single ? "p-4" : "p-3",
                                    !single && isSelected && "border-brand-cyan",
                                )}
                            >
                                {!single && (
                                <>
                                <div className="flex flex-wrap items-center gap-1.5">
                                    <SeverityBadge severity={item.severity} />
                                    {item.maxCvss !== null && (
                                        <span className="rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-0.5 text-[10px] text-[#9eacbd]">CVSS {item.maxCvss}</span>
                                    )}
                                    {item.nodeIds.length > 1 && (
                                        <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] font-bold text-[#94a3b8]">×{item.nodeIds.length}</span>
                                    )}
                                </div>
                                <h3 className="m-0 mt-2 text-[13px] leading-snug font-semibold tracking-normal! text-foreground [font-family:inherit]!">{item.title}</h3>
                                </>
                                )}
                                <p className={cn("m-0 text-[11px] text-[#94a3b8]", !single && "mt-1")}>Found on: {item.origins.join(", ")}</p>
                                {detail?.description && (
                                    <section className="mt-3">
                                        <h4 className="m-0 mb-1 text-[10px] font-semibold tracking-wide text-[#94a3b8] uppercase">Description</h4>
                                        <p className="m-0 text-[12px] leading-relaxed text-[#cbd5e1]">{detail.description}</p>
                                    </section>
                                )}
                                {detail?.recommendation && (
                                    <section className="mt-3">
                                        <h4 className="m-0 mb-1 text-[10px] font-semibold tracking-wide text-[#94a3b8] uppercase">How to fix</h4>
                                        <p className="m-0 text-[12px] leading-relaxed text-[#cbd5e1]">{detail.recommendation}</p>
                                    </section>
                                )}
                                <button type="button" onClick={() => onShowOnGraph(item.nodeIds[0])}
                                    className="mt-3 inline-flex items-center gap-1 text-[11px] font-semibold text-brand-cyan hover:underline">
                                    Show on graph <ChevronRight className="size-3.5" />
                                </button>
                            </article>
                        );
                    })}
                </div>
        </SidePanelShell>
    );
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

function GraphLegend() {
    const item = "flex items-center gap-2 whitespace-nowrap text-[#cbd5e1]";
    return (
        <div className="flex flex-col gap-2 rounded-lg border border-brand-panel-border bg-[#0b1625]/60 px-3 py-2.5 text-[11px]">
            <h3 className="m-0 text-[10px] font-semibold tracking-wide text-[#94a3b8] uppercase">Legend</h3>
            <div className="grid grid-cols-3 gap-x-5 gap-y-1.5">
                <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
                    <li className={item}><span className="h-3 w-4 shrink-0 rounded-[4px] border border-brand-cyan/60 bg-brand-cyan/10" /> Host</li>
                    <li className={item}><span className="h-2.5 w-4 shrink-0 rounded-[3px] border border-[#a855f7]/60 bg-[#a855f7]/15" /> Port</li>
                    <li className={item}><span className="h-3 w-4 shrink-0 rounded-[4px] border border-brand-success/60 bg-brand-success/10" /> Technology</li>
                    <li className={item}>
                        <span className="flex shrink-0 gap-0.5">
                            <span className="h-3 w-[3px] rounded-full bg-[#ef4444]" />
                            <span className="h-3 w-[3px] rounded-full bg-[#f97316]" />
                            <span className="h-3 w-[3px] rounded-full bg-[#60a5fa]" />
                        </span>
                        <span title="Stripe colour = severity">Finding</span>
                    </li>
                </ul>
                <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
                    <li className={item}><span className="h-1.5 w-4 shrink-0 animate-pulse rounded-full bg-brand-yellow" /> Worker running</li>
                    <li className={item}><span className="h-1.5 w-4 shrink-0 rounded-full bg-brand-success" /> Step done</li>
                    <li className={item}><span className="size-2.5 shrink-0 animate-pulse rounded-full bg-brand-cyan shadow-[0_0_8px_rgba(43,216,245,0.6)]" /> Just found</li>
                </ul>
                <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
                    <li className={item}>
                        <svg width="16" height="6" aria-hidden="true" className="shrink-0"><line x1="0" y1="3" x2="16" y2="3" className="stroke-brand-cyan/70" strokeWidth="1.5" /></svg>
                        Link
                    </li>
                    <li className={item}>
                        <svg width="16" height="6" aria-hidden="true" className="shrink-0"><line x1="0" y1="3" x2="16" y2="3" className="stroke-brand-success/70" strokeWidth="1.5" strokeDasharray="3 3" /></svg>
                        Context (runs on)
                    </li>
                    <li className={item}>
                        <svg width="16" height="6" aria-hidden="true" className="shrink-0"><line x1="0" y1="3" x2="16" y2="3" className="stroke-[#f97316]" strokeWidth="1.5" /></svg>
                        CVE link
                    </li>
                </ul>
            </div>
        </div>
    );
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
function DetailsPanel({
    node,
    edges,
    findingsByEntityId,
    onClose,
}: {
    node: GraphNode;
    edges: GraphEdge[];
    findingsByEntityId: Map<string, DashboardFindingItem>;
    onClose: () => void;
}) {
    const visual = nodeVisual(node);
    const Icon = visual.icon;

    const findingDetail = node.type === "finding" && node.entity_id ? findingsByEntityId.get(node.entity_id) : undefined;
    const incoming = edges.filter((e)=> e.target === node.id).length;
    const outgoing = edges.filter((e)=> e.source === node.id).length;
    const sourceEdge = edges.find((e)=> e.target === node.id);

    return (
        <>
            <header className="flex items-start justify-between gap-3 border-b border-brand-panel-border p-4">
                <div className="flex min-w-0 items-start gap-3">
                    <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg border", visual.border, visual.iconBg, visual.text)}>
                        <Icon className="size-4.5" />
                    </span>
                    <div className="min-w-0">
                        <h2 id="node-panel-title" className="m-0 text-base leading-snug font-semibold break-all tracking-normal! text-foreground [font-family:inherit]!">{node.label}</h2>
                        <p className="m-0 mt-0.5 text-[11px] text-[#94a3b8]">{nodeSublabel(node)}</p>
                        {node.type === "finding" ? (
                            <div className="mt-2 flex flex-wrap gap-1.5">
                                <SeverityBadge severity={normalizeSeverity(node.risk.severity)} />
                                {node.risk.max_cvss !== null && (
                                    <span className="rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-0.5 text-[10px] text-[#9eacbd]">CVSS {node.risk.max_cvss}</span>
                                )}
                                {typeof node.metadata.cve_id === "string" && node.metadata.cve_id && (
                                    <span className="rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-0.5 text-[10px] text-[#9eacbd]">{node.metadata.cve_id}</span>
                                )}
                            </div>
                        ) : node.risk.finding_count > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1.5">
                                <SeverityBadge severity={normalizeSeverity(node.risk.severity)} />
                                <span className="rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-0.5 text-[10px] text-[#9eacbd]">
                                    {node.risk.finding_count} finding{node.risk.finding_count === 1 ? "" : "s"}
                                </span>
                            </div>
                        )}
                    </div>
                </div>
                <button type="button" onClick={onClose} aria-label="Close details"
                    className="grid size-8 shrink-0 place-items-center rounded-lg text-[#94a3b8] hover:bg-white/5 hover:text-foreground">
                    <X className="size-4" />
                </button>
            </header>

            <div className="min-h-0 overflow-y-auto overscroll-contain p-4">
                <div className="flex flex-col gap-4 rounded-lg border border-[#22324d] bg-[#0f1c30] p-4">
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
                        <h3 className="m-0 mb-1.5 text-[10px] font-semibold tracking-wide text-[#94a3b8] uppercase">Description</h3>
                        <p className="m-0 text-[12px] leading-relaxed text-[#cbd5e1]">
                            {findingDetail?.description ?? nodeDescription(node) ?? "No description available."}
                        </p>
                    </section>

                    {node.type === "finding" && findingDetail?.recommendation && (
                        <section>
                            <h3 className="m-0 mb-1.5 text-[10px] font-semibold tracking-wide text-[#94a3b8] uppercase">How to fix</h3>
                            <p className="m-0 text-[12px] leading-relaxed text-[#cbd5e1]">{findingDetail.recommendation}</p>
                        </section>
                    )}
                </div>
            </div>
        </>
    );
}

function WorkerActivityTable ({ sources }: { sources: ScanSourceStatus[] }) {
    const visibleSources = sources.filter((s) => s.source_name !== "hunter.io" && s.source_name !== "cpe_resolver");
    
    return(
        <Card className="border border-brand-panel-border bg-brand-panel max-sm:hidden">
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

const FINDINGS_PAGE_SIZE = 100;
async function fetchAllScanFindings(scanId: string): Promise<DashboardFindingItem[]> {
    const all: DashboardFindingItem[] = [];
    for (let offset = 0; offset < 5000; offset += FINDINGS_PAGE_SIZE) {
        const page = await fetchScanFindings(scanId, { limit: FINDINGS_PAGE_SIZE, offset });
        all.push(...page);
        if (page.length < FINDINGS_PAGE_SIZE) break;
    }
    return all;
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

    const [previousScanId, setPreviousScanId] = useState<string | null>(null);
    const [compare, setCompare] = useState<GraphCompareResponse | null>(null);
    const [compareLoading, setCompareLoading] = useState(false);
    const [compareError, setCompareError] = useState<string | null>(null);
    const [showCompare, setShowCompare] = useState(false);
    const [rowOrder, setRowOrder] = useState<"auto" | "discovery" | "risk">("auto");
    const [collapsedRows, setCollapsedRows] = useState<Set<string>>(new Set());
    const autoCollapsedRef = useRef(false);

    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const newIdsTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const prevNodeIdsRef = useRef<Set<string>>(new Set());

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

        fetchAllScanFindings(id).then(setFindings).catch(()=>{});
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

    const rows = useMemo(() => buildRows(graph), [graph]);
    const nodesById = useMemo(() => new Map((graph?.nodes ?? []).map((n) => [n.id, n])), [graph]);
    const findingsByEntityId = useMemo(() => new Map(findings.map((f) => [f.id, f])), [findings]);
    const findingSources = useMemo(() => new Map(findings.map((f) => [f.id, f.source])), [findings]);
    const domainNode = graph?.nodes.find((n) => n.type === "domain");

    const edges = useMemo(() => graph?.edges ?? [], [graph]);

    const scanFinished = scan ? TERMINAL_SCAN_STATUSES.has(scan.status) : false;
    useEffect(() => {
        if (!scanFinished || autoCollapsedRef.current || rows.length === 0) return;
        autoCollapsedRef.current = true;
        setCollapsedRows(new Set(rows
            .filter((row) => !row.isApex && ![...row.nodeIds].some((id) => nodesById.get(id)?.type === "finding"))
            .map((row) => row.id)));
    }, [scanFinished, rows, nodesById]);

    const [flashRowId, setFlashRowId] = useState<string | null>(null);
    const [openFindings, setOpenFindings] = useState<{ rowId: string; category: FindingCategoryKey; itemKey: string } | null>(null);
    const [panelNodeId, setPanelNodeId] = useState<string | null>(null);
    const closeNodePanel = useCallback(() => setPanelNodeId(null), []);
    function openNodePanel(nodeId: string) {
        setSelectedId(nodeId);
        setOpenFindings(null);
        setPanelNodeId(nodeId);
    }
    const closeFindings = useCallback(() => setOpenFindings(null), []);
    const flashTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    useEffect(() => () => { if (flashTimeoutRef.current) clearTimeout(flashTimeoutRef.current); }, []);

    function jumpToNode(nodeId: string) {
        setSelectedId(nodeId);
        const row = rows.find((r) => r.root.id === nodeId)
            ?? rows.find((r) => !r.isApex && r.nodeIds.has(nodeId))
            ?? rows.find((r) => r.nodeIds.has(nodeId));
        if (!row) return;
        setCollapsedRows((prev) => {
            const next = new Set(prev);
            next.delete(row.id);
            return next;
        });
        setFlashRowId(row.id);
        if (flashTimeoutRef.current) clearTimeout(flashTimeoutRef.current);
        flashTimeoutRef.current = setTimeout(() => setFlashRowId(null), 1800);
        requestAnimationFrame(() => {
            document.getElementById(`graph-row-${row.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
        });
    }

    const findingParam = searchParams.get("finding");
    const focusNodeId = findingParam ? `finding:${findingParam}` : searchParams.get("node");
    const focusHandledRef = useRef<string | null>(null);
    useEffect(() => {
        if (!focusNodeId || focusHandledRef.current === focusNodeId) return;
        if (!rows.some((row) => row.nodeIds.has(focusNodeId))) return;
        focusHandledRef.current = focusNodeId;
        jumpToNode(focusNodeId);
    });

    function toggleRow(rowId: string) {
        setCollapsedRows((prev) => {
            const next = new Set(prev);
            if (next.has(rowId)) next.delete(rowId); else next.add(rowId);
            return next;
        });
    }

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

    const assetsDiscovered = summary
        ? summary.counts.assets + summary.counts.services + summary.counts.technologies
        : graph?.nodes.filter((n) => n.type === "asset" || n.type === "service" || n.type === "technology").length ?? 0;
    const findingsTotal = summary?.counts.findings ?? domainNode?.risk.finding_count ?? 0;
    const criticalCount = summary?.risk.critical_findings
        ?? graph?.nodes.filter((n) => n.type === "finding" && n.risk.severity === "critical").length ?? 0;
    const isRunning = !TERMINAL_SCAN_STATUSES.has(scan.status);

    const addedNodeIds = showCompare && compare ? new Set(compare.added_nodes) : null;

    const sourcesByName = new Map(scan.sources.map((s) => [s.source_name, s]));
    const effectiveOrder = rowOrder === "auto" ? (isRunning ? "discovery" : "risk") : rowOrder;
    const [apexRow, ...subdomainRows] = rows;
    const orderedRows = apexRow ? [apexRow, ...[...subdomainRows].sort((a, b) =>
        effectiveOrder === "risk"
            ? rowRiskScore(b, nodesById) - rowRiskScore(a, nodesById) || a.root.label.localeCompare(b.root.label)
            : a.discoveredAt.localeCompare(b.discoveredAt) || a.root.label.localeCompare(b.root.label),
    )] : [];
    const hasGraphData = rows.some((row) => row.nodeIds.size > 1) || subdomainRows.length > 0;

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
        <Card className="overflow-visible border border-brand-panel-border bg-brand-panel">
            <CardContent className="flex flex-col gap-4">
                <div>
                    <h2 className="m-0 text-sm font-bold tracking-[0.15em] text-foreground/90 uppercase">
                        Live Scan Graph
                        <span className="ml-2 font-semibold tracking-normal text-[#94a3b8] normal-case">
                            · {subdomainRows.length} subdomain{subdomainRows.length === 1 ? "" : "s"}
                        </span>
                    </h2>
                    <p className="mt-1 text-[11px] text-[#94a3b8]">
                        Each subdomain has its own graph, built live as workers find hosts, ports, findings and technologies. Hover to trace a path; click for details.
                    </p>
                </div>

                <div className="flex flex-wrap items-stretch gap-3">
                <div className="flex w-fit max-w-full flex-col gap-2.5 rounded-lg border border-brand-panel-border bg-[#0b1625]/60 px-3 py-2.5">
                    <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
                        <span className="flex items-center gap-2">
                            <span className="text-[10px] font-semibold tracking-wide text-[#94a3b8] uppercase">View</span>
                            <span className="inline-flex overflow-hidden rounded-md border border-brand-panel-border">
                                {([["discovery", "Discovery order"], ["risk", "Riskiest first"]] as const).map(([key, label]) => (
                                    <button
                                        key={key}
                                        type="button"
                                        onClick={() => setRowOrder(key)}
                                        aria-pressed={effectiveOrder === key}
                                        className={cn(
                                            "px-2.5 py-1 text-[11px] font-semibold",
                                            effectiveOrder === key ? "bg-brand-cyan/10 text-brand-cyan" : "text-[#94a3b8] hover:text-foreground",
                                        )}
                                    >
                                        {label}
                                    </button>
                                ))}
                            </span>
                        </span>
                        <span className="flex items-center gap-2">
                            <span className="text-[10px] font-semibold tracking-wide text-[#94a3b8] uppercase">Rows</span>
                            <span className="inline-flex overflow-hidden rounded-md border border-brand-panel-border">
                                <button
                                    type="button"
                                    onClick={() => setCollapsedRows(new Set())}
                                    className="px-2.5 py-1 text-[11px] font-semibold text-[#94a3b8] hover:text-foreground"
                                >
                                    Expand all
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setCollapsedRows(new Set(rows.map((row) => row.id)))}
                                    className="border-l border-brand-panel-border px-2.5 py-1 text-[11px] font-semibold text-[#94a3b8] hover:text-foreground"
                                >
                                    Collapse all
                                </button>
                            </span>
                        </span>
                        {previousScanId && (
                            <button
                                type="button"
                                onClick={toggleCompare}
                                aria-pressed={showCompare}
                                className={cn(
                                    "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[11px] font-semibold",
                                    showCompare ? "border-brand-success/40 bg-brand-success/10 text-brand-success" : "border-brand-panel-border text-[#94a3b8] hover:text-foreground",
                                )}
                            >
                                <GitCompare size={13} />
                                Compare with previous scan
                            </button>
                        )}
                    </div>

                    {summary && summary.concentrations.length > 0 && (
                        <div className="border-t border-brand-panel-border pt-2.5">
                            <HotSpotPills concentrations={summary.concentrations} onSelect={jumpToNode} />
                        </div>
                    )}
                </div>

                <GraphLegend />

                <div className="grid grid-cols-2 grid-rows-2 gap-2">
                    {statChips.map((chip) => {
                        const isProgress = chip.label === "Scan Progress";
                        return (
                            <div key={chip.label} className="flex min-w-[180px] items-center gap-2.5 rounded-lg border border-brand-panel-border bg-[#0b1625]/60 px-3 py-2">
                                <span className={cn("flex size-7 shrink-0 items-center justify-center rounded-md border", chip.accent.border, chip.accent.iconBg, chip.accent.text)}>
                                    {isProgress && !isRunning ? <CheckCircle2 className="size-3.5" /> : <chip.icon className="size-3.5" />}
                                </span>
                                <div className="flex min-w-0 flex-1 flex-col">
                                    <strong className={cn("text-base leading-tight", isProgress && !isRunning ? "text-brand-success" : "text-foreground")}>
                                        {isProgress && !isRunning ? "Complete" : chip.value}
                                    </strong>
                                    <span className="text-[10px] leading-tight tracking-wide text-[#94a3b8] uppercase">{chip.label}</span>
                                    {isProgress && isRunning && (
                                        <span className="mt-1 h-1 overflow-hidden rounded-full bg-white/10">
                                            <span className="block h-full rounded-full bg-brand-success transition-[width] duration-700" style={{ width: `${scan.progress}%` }} />
                                        </span>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
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

                {!hasGraphData ? (
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
                    <div className="flex flex-col gap-3">
                        <RowsHeader />
                        {orderedRows.map((row) => (
                            <SubdomainRow
                                key={row.id}
                                row={row}
                                stages={rowStages(row, nodesById, sourcesByName, isRunning)}
                                sources={scan.sources}
                                scanRunning={isRunning}
                                nodesById={nodesById}
                                selectedId={selectedId}
                                newIds={newIds}
                                addedNodeIds={addedNodeIds}
                                collapsed={collapsedRows.has(row.id)}
                                flash={flashRowId === row.id}
                                onToggleCollapsed={() => toggleRow(row.id)}
                                onSelect={openNodePanel}
                                onOpenFinding={(rowId, category, itemKey) => setOpenFindings({ rowId, category, itemKey })}
                                findingSources={findingSources}
                            />
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );

    const openFindingsRow = openFindings ? rows.find((r) => r.id === openFindings.rowId) : undefined;
    const openFindingsCategory = openFindingsRow
        ? buildRowView(openFindingsRow, nodesById, findingSources).categories.find((c) => c.key === openFindings?.category)
        : undefined;
    const findingsPanel = openFindingsRow && openFindingsCategory ? (
        <FindingsPanel
            rowLabel={openFindingsRow.root.label}
            category={openFindingsCategory}
            focusItemKey={openFindings?.itemKey ?? null}
            nodesById={nodesById}
            findingsByEntityId={findingsByEntityId}
            selectedId={selectedId}
            onShowOnGraph={(nodeId) => { closeFindings(); jumpToNode(nodeId); }}
            onClose={closeFindings}
        />
    ) : null;

    const panelNode = panelNodeId ? nodesById.get(panelNodeId) : undefined;
    const nodePanel = panelNode ? (
        <SidePanelShell labelledBy="node-panel-title" onClose={closeNodePanel}>
            <DetailsPanel
                key={panelNode.id}
                node={panelNode}
                edges={edges}
                findingsByEntityId={findingsByEntityId}
                onClose={closeNodePanel}
            />
        </SidePanelShell>
    ) : null;

    return (
        <div className={variant === "standalone" ? "mx-auto flex w-full max-w-[1700px] flex-col gap-6" : "flex min-w-0 flex-col gap-6"}>
            {variant === "standalone" && (
                <>
                    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Link href="/phase2_scan" className="hover:text-foreground hover:underline">Scans</Link>
                        <ChevronRight className="size-4" />
                        <span>{scan.domain}</span>
                        <ChevronRight className="size-4" />
                        <span className="text-foreground">Scan Graph</span>
                    </nav>

                    <div className="flex flex-wrap items-start justify-between gap-4">
                        <div>
                            <div className="flex flex-wrap items-center gap-3">
                                <h1 className="text-2xl font-semibold text-foreground">{scan.domain}</h1>
                                <Badge className="bg-brand-cyan text-black capitalize">{scan.status}</Badge>
                                {isRunning && (
                                    <span className="inline-flex items-center gap-1.5 text-[11px] text-brand-cyan">
                                        <span className="size-1.5 animate-pulse rounded-full bg-brand-cyan" />
                                        Live
                                    </span>
                                )}
                            </div>
                            <p className="mt-1 text-sm text-muted-foreground">
                                {scanTypeLabel[scan.scan_type] ?? scan.scan_type} &bull; {scan.progress}% complete
                            </p>
                        </div>
                        <Link
                            href={`/phase2_scan/progress?scan_id=${scanId}`}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-brand-panel-border px-4 py-2.5 text-sm text-foreground hover:border-brand-cyan hover:text-brand-cyan"
                        >
                            View worker timeline
                        </Link>
                    </div>
                </>
            )}

            {error && <p className="text-xs text-brand-alert">{error}</p>}
            {findingsPanel}
            {nodePanel}

            {variant === "standalone" ? (
                <>
                    {graphCard}
                    <WorkerActivityTable sources={scan.sources} />
                </>
            ) : (
                <>
                    {graphCard}
                </>
            )}
        </div>
    );

}