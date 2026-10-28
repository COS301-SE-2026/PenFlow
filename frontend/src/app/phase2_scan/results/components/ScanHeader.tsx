"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Check, ChevronDown, Download, FileText, Link2, Loader2, Mail } from "lucide-react";

import { fetchScanStatus, getReportPdfUrl, sendReportEmail, type RealTimeScanStatus } from "@/lib/scanService";
import { formatDateWithYear } from "@/lib/engagementFormat";
import { cn } from "@/lib/utils";
import ScanTabs from "./ScanTabs";

const scanTypeLabel: Record<string, string> = {
    active_vulnerability: "Active Vulnerability Scan",
    passive_ctem: "Passive Reconnaissance",
};

const REPORT_POLL_MS = 5000;
const MAX_REPORT_CHECKS_AFTER_SCAN = 24;
const TERMINAL_SCAN_STATUSES = new Set(["completed", "failed", "partial"]);

type ReportState = "ready" | "preparing" | "awaiting_scan" | "failed";
type DownloadFeedback = "idle" | "downloading" | "done" | "error";

function reportState(scan: RealTimeScanStatus | null, gaveUp = false): ReportState {
    const report = scan?.report_status;
    if (report?.pdf_path || report?.status === "completed") return "ready";
    if (report?.status === "failed" || gaveUp) return "failed";
    if (scan && !TERMINAL_SCAN_STATUSES.has(scan.status)) return "awaiting_scan";
    return "preparing";
}

export default function ScanHeader({scanId}: {scanId: string}) {
    const [scan, setScan] = useState<RealTimeScanStatus | null>(null);
    const [feedback, setFeedback] = useState<DownloadFeedback>("idle");
    const [menuOpen, setMenuOpen] = useState(false);
    const [emailOpen, setEmailOpen] = useState(false);
    const [email, setEmail] = useState("");
    const [emailState, setEmailState] = useState<"idle" | "sending" | "sent" | "error">("idle");
    const [copied, setCopied] = useState(false);
    const [gaveUp, setGaveUp] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);
    const feedbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    const state = reportState(scan, gaveUp);

    useEffect(() => {
        let cancelled = false;
        let timer: ReturnType<typeof setTimeout> | null = null;
        let checksAfterScan = 0;
        const load = () => {
            fetchScanStatus(scanId)
                .then((result) => {
                    if (cancelled) return;
                    setScan(result);
                    const current = reportState(result);
                    if (current === "preparing") checksAfterScan += 1;
                    if (current === "preparing" && checksAfterScan > MAX_REPORT_CHECKS_AFTER_SCAN) {
                        setGaveUp(true);
                        return;
                    }
                    if (current === "preparing" || current === "awaiting_scan") timer = setTimeout(load, REPORT_POLL_MS);
                })
                .catch(() => { if (!cancelled) setScan(null); });
        };
        load();
        return () => {
            cancelled = true;
            if (timer) clearTimeout(timer);
        };
    }, [scanId]);

    useEffect(() => () => { if (feedbackTimer.current) clearTimeout(feedbackTimer.current); }, []);

    useEffect(() => {
        if (!menuOpen) return;
        const onPointerDown = (e: PointerEvent) => {
            if (!menuRef.current?.contains(e.target as Node)) { setMenuOpen(false); setEmailOpen(false); }
        };
        const onKeyDown = (e: KeyboardEvent) => { if (e.key === "Escape") { setMenuOpen(false); setEmailOpen(false); } };
        document.addEventListener("pointerdown", onPointerDown);
        document.addEventListener("keydown", onKeyDown);
        return () => {
            document.removeEventListener("pointerdown", onPointerDown);
            document.removeEventListener("keydown", onKeyDown);
        };
    }, [menuOpen]);

    const domain = scan?.domain ?? "...";
    const scanType = scan ? (scanTypeLabel[scan.scan_type] ?? scan.scan_type) : "";
    const scanDate = scan?.created_at ? formatDateWithYear(scan.created_at) : "";
    const fileName = `penflow-${scan?.domain ?? "scan"}-${scan?.created_at?.slice(0, 10) ?? "report"}.pdf`;

    const flashFeedback = useCallback((value: DownloadFeedback) => {
        setFeedback(value);
        if (feedbackTimer.current) clearTimeout(feedbackTimer.current);
        feedbackTimer.current = setTimeout(() => setFeedback("idle"), 2500);
    }, []);

    async function handleDownload() {
        if (state !== "ready" || feedback === "downloading") return;
        setFeedback("downloading");
        try {
            const response = await fetch(getReportPdfUrl(scanId), { credentials: "include" });
            if (!response.ok) throw new Error(`Download failed (${response.status})`);
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = fileName;
            document.body.appendChild(link);
            link.click();
            link.remove();
            setTimeout(() => URL.revokeObjectURL(url), 0);
            flashFeedback("done");
        } catch {
            flashFeedback("error");
        }
    }

    async function handleSendEmail(e: React.FormEvent) {
        e.preventDefault();
        if (!email.trim()) return;
        setEmailState("sending");
        try {
            await sendReportEmail(scanId, email.trim());
            setEmailState("sent");
        } catch {
            setEmailState("error");
        }
    }

    async function handleCopyLink() {
        try {
            await navigator.clipboard.writeText(`${window.location.origin}/report/${scanId}`);
            setCopied(true);
            setTimeout(() => setCopied(false), 1800);
        } catch {
        }
    }

    const label = state === "awaiting_scan" ? "Report after scan completes"
        : state === "preparing" ? "Preparing report…"
        : state === "failed" ? "Report unavailable"
        : feedback === "downloading" ? "Downloading…"
        : feedback === "done" ? "Downloaded"
        : feedback === "error" ? "Download failed — retry"
        : "Download report";
    const Icon = state === "preparing" || feedback === "downloading" ? Loader2
        : state === "failed" || feedback === "error" ? AlertTriangle
        : feedback === "done" ? Check
        : Download;
    const spinning = state === "preparing" || feedback === "downloading";
    const failedReason = scan?.report_status?.error_message
        ?? (scan?.report_status ? "The report could not be generated for this scan." : "No report was generated for this scan.");
    const menuItem = "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] text-[#cbd5e1] no-underline hover:bg-white/5 hover:text-foreground";

    const reportActions = (
            <div ref={menuRef} className="relative flex shrink-0 max-sm:hidden">
                <button
                    type="button"
                    onClick={handleDownload}
                    disabled={state !== "ready" || feedback === "downloading"}
                    title={state === "failed" ? failedReason : undefined}
                    aria-live="polite"
                    className={cn(
                        "inline-flex h-10 items-center gap-2 rounded-l-lg px-4 text-sm font-semibold transition-colors disabled:cursor-not-allowed",
                        state === "ready" && feedback !== "error" && "bg-brand-cyan text-[#04121f] hover:bg-brand-cyan/85",
                        state === "ready" && feedback === "error" && "bg-brand-alert/15 text-brand-alert ring-1 ring-brand-alert/50 ring-inset",
                        state !== "ready" && "bg-brand-panel-deep text-[#94a3b8] ring-1 ring-brand-panel-border ring-inset",
                        state === "failed" && "text-brand-alert",
                    )}
                >
                    <Icon className={cn("size-4", spinning && "animate-spin")} />
                    {label}
                    {state === "ready" && feedback === "idle" && <span className="text-[11px] font-normal opacity-70">PDF</span>}
                </button>
                <button
                    type="button"
                    onClick={() => { setMenuOpen((prev) => !prev); setEmailOpen(false); }}
                    aria-haspopup="menu"
                    aria-expanded={menuOpen}
                    aria-label="More report options"
                    className={cn(
                        "inline-flex h-10 items-center rounded-r-lg border-l px-2.5 transition-colors",
                        state === "ready"
                            ? "border-[#04121f]/20 bg-brand-cyan text-[#04121f] hover:bg-brand-cyan/85"
                            : "border-brand-panel-border bg-brand-panel-deep text-[#94a3b8] ring-1 ring-brand-panel-border ring-inset hover:text-foreground",
                    )}
                >
                    <ChevronDown className={cn("size-4 transition-transform", menuOpen && "rotate-180")} />
                </button>

                {menuOpen && (
                    <div role="menu" className="absolute top-full right-0 z-30 mt-1.5 w-64 rounded-lg border border-brand-panel-border bg-[#0b1625] p-1.5 shadow-[0_12px_32px_rgba(0,0,0,0.6)]">
                        {emailOpen ? (
                            <form onSubmit={handleSendEmail} className="flex flex-col gap-2 p-1.5">
                                <label htmlFor="report-email" className="text-[11px] font-semibold text-[#cbd5e1]">Email the report to</label>
                                <input
                                    id="report-email"
                                    type="email"
                                    inputMode="email"
                                    autoComplete="email"
                                    autoFocus
                                    value={email}
                                    onChange={(e) => { setEmail(e.target.value); setEmailState("idle"); }}
                                    placeholder="you@company.com"
                                    className="h-9 rounded-md border border-brand-panel-border bg-brand-panel-deep px-2.5 text-[13px] text-foreground outline-none focus:border-brand-cyan"
                                />
                                <div className="flex items-center justify-between gap-2">
                                    <button type="button" onClick={() => setEmailOpen(false)} className="text-[12px] text-[#94a3b8] hover:text-foreground">Back</button>
                                    <button
                                        type="submit"
                                        disabled={!email.trim() || emailState === "sending" || emailState === "sent"}
                                        className="inline-flex h-8 items-center gap-1.5 rounded-md bg-brand-cyan px-3 text-[12px] font-semibold text-[#04121f] disabled:opacity-50"
                                    >
                                        {emailState === "sending" ? <Loader2 className="size-3.5 animate-spin" /> : emailState === "sent" ? <Check className="size-3.5" /> : <Mail className="size-3.5" />}
                                        {emailState === "sent" ? "Sent" : "Send"}
                                    </button>
                                </div>
                                {emailState === "error" && <p className="m-0 text-[11px] text-brand-alert">Couldn&apos;t send the email. Try again.</p>}
                            </form>
                        ) : (
                            <>
                                <button type="button" role="menuitem" onClick={() => setEmailOpen(true)} className={menuItem}>
                                    <Mail className="size-4 text-[#94a3b8]" /> Email report…
                                </button>
                                <Link href={`/report/${scanId}`} role="menuitem" className={menuItem}>
                                    <FileText className="size-4 text-[#94a3b8]" /> Open report summary
                                </Link>
                                <button type="button" role="menuitem" onClick={handleCopyLink} className={menuItem}>
                                    {copied ? <Check className="size-4 text-brand-success" /> : <Link2 className="size-4 text-[#94a3b8]" />}
                                    {copied ? "Link copied" : "Copy report link"}
                                </button>
                                {state !== "ready" && (
                                    <p className="m-0 border-t border-brand-panel-border px-2.5 pt-2 pb-1 text-[11px] text-[#94a3b8]">
                                        {state === "preparing" ? "The PDF is still being generated — the download unlocks automatically."
                                            : state === "awaiting_scan" ? "The report is generated when the scan finishes — the download unlocks automatically."
                                            : failedReason}
                                    </p>
                                )}
                            </>
                        )}
                    </div>
                )}
            </div>
    );

    return (
        <>
        <header className="flex items-center justify-between gap-6">
            <div className="min-w-0">
                <div className="flex items-center gap-3 max-sm:gap-2">
                    <h1 className="m-0 truncate text-[28px] text-foreground max-sm:text-lg">{domain}</h1>
                    {scan && (
                        <span className={cn(
                            "shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase capitalize max-sm:px-2 max-sm:py-0.5",
                            scan.status === "partial" ? "border-brand-yellow/60 bg-brand-yellow/10 text-brand-yellow"
                                : scan.status === "failed" ? "border-brand-alert/60 bg-brand-alert/10 text-brand-alert"
                                : scan.status === "completed" ? "border-brand-success/60 bg-brand-success/10 text-brand-success"
                                : "border-brand-cyan/60 bg-brand-cyan/10 text-brand-cyan"
                        )}>
                            {scan.status}
                        </span>
                    )}
                    <button
                        type="button"
                        onClick={handleDownload}
                        disabled={state !== "ready" || feedback === "downloading"}
                        aria-label={label}
                        title={state === "failed" ? failedReason : label}
                        className={cn(
                            "hidden size-8 shrink-0 items-center justify-center rounded-lg max-sm:inline-flex",
                            state === "ready" ? "bg-brand-cyan text-[#04121f] hover:bg-brand-cyan/85" : "border border-brand-panel-border text-[#94a3b8]",
                        )}
                    >
                        <Icon className={cn("size-4", spinning && "animate-spin")} />
                    </button>
                </div>
                <p className="mt-2.5 flex items-center gap-2 text-sm text-muted-foreground max-sm:mt-1 max-sm:text-xs">
                    <span>{scanType}</span>
                    {scanDate && <span>· {scanDate}</span>}
                </p>
            </div>

        </header>
        <ScanTabs scanId={scanId} actions={reportActions} />
        </>
    );
}