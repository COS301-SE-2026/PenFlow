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