"use client";
import type {ReactNode} from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Ban, Binoculars, Bug, ChevronRight, Crosshair, FileSearch, Fingerprint, Globe, Info, Lock, Network, ShieldAlert,
         ShieldCheck, type LucideIcon,} from "lucide-react";

import { Card, CardContent} from "@/components/ui/card";
import {Badge} from "@/components/ui/badge";
import {Button} from "@/components/ui/button";
import {cn} from "@/lib/utils";
import radarStyles from "@app/scan/components/ScanConsoleSection.module.css";
import {fetchScanStatus, type RealTimeScanStatus} from "@/lib/scanService";

type SourceStatus = "pending" | "running" | "completed" | "failed" | "partial"| "skipped";
type SourcePhase = "idle" | "line" | "done";

const POLL_INTERVAL_MS = 4000;
const TERMINAL_SCAN_STATUSES = new Set(["completed", "failed", "partial"]);
const TERMINAL_SOURCE_STATUSES = new Set<SourceStatus>(["completed", "failed", "parial", "skipped"]);
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
    "crt.sh": { label: "crt.sh", description: "Searches Certificate Transparency logs for issued certificates and realated. ", icon: FileSearch},
    urlscan: { label: "URLScan", description: "Queries urlscan.io for prior scans and page metadata for the domain.", icon: Globe},
    wappalyzer: { label: "Wappalyzer", description: "Identifies web technologies used by the target.", icon: Fingerprint},
    shodan: { label: "Shodan", description: "Queries Shodan for exposed devices, banners, and services tied to the target's IP.", icon: Fingerprint},
    hibp: { label: "HaveIBeenPwned", description: "Checks associated email addresses and domains against known data breach databases", icon: ShieldAlert},
    target_resolution: { label: "Resolving Target", description: "Resolves the verified domain into IPv4 and IPv6 addresses.", icon: Globe},
    nmap: { label: "Discovering ports", description: "Checks wheter the host is reachable and discovers open ports and network services.", icon: Crosshair},
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

const sourceStatusConfig: Record<SourceStatus, {label: string; className: string}> = {
    pending: {label: "Pending", className: "border-muted-foreground/30 text-muted-foreground bg-muted/40"},
    running: {label: "Running", className: "border-brand-cyan text-brand-cyan bg-brand-cyan/10"},
    completed: {label: "Completed", className: "border-brand-success text-brand-success bg-brand-success/10"},
    failed: {label: "Failed", className: "border-brand-alert text-brand-alert bg-brand-alert/10"},
    partial: {label: "Partial", className: "border-brand-yellow text-brand-yellow bg-brand-yellow/10"},
    skipped: {label: "Skipped", className: "border-muted-foreground/30 text-muted-foreground bg-muted/40"},
};

const dotToneClassName: Record<SourceStatus, string> ={
    pending: "bg-muted-foreground/40",
    running: "bg-brand-cyan animate-pulse",
    completed: "bg-brand-success",
    failed: "bg-brand-alert",
    partial: "bg-brand-yellow",
    skipped: "bg-muted-foreground/40",
};

