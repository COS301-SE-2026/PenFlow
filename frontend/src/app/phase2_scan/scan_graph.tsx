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
