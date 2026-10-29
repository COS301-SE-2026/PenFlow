"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import NavBar from "@/components/NavBar";
import { fetchScanHistory, getReportPdfUrl } from "@/lib/scanService";
import type { ScanHistoryItem } from "@/lib/scanService";
import styles from "./history.module.css";
import {
  AlertTriangle, Check, CheckCircle2, ChevronDown, Crosshair, Globe, Download, FileText, Loader2, Mail,
  Satellite, ShieldCheck, type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDateWithYear } from "@/lib/engagementFormat";
import EmailReportDialog from "@/shared/components/EmailReportDialog";
import { fetch_domains } from "@/lib/domainServices";

type TypeFilter = "all" | "active" | "passive";

const TYPE_INFO: Record<string, { label: string; short: string; icon: LucideIcon; className: string; key: Exclude<TypeFilter, "all"> }> = {
  active_vulnerability: { label: "Active scan", short: "Active", icon: Crosshair, className: "border-brand-cyan/40 bg-brand-cyan/10 text-brand-cyan", key: "active" },
  passive_ctem: { label: "Passive scan", short: "Passive", icon: Satellite, className: "border-[#a78bfa]/40 bg-[#a78bfa]/10 text-[#a78bfa]", key: "passive" },
};
const typeInfo = (scanType: string) => TYPE_INFO[scanType] ?? TYPE_INFO.passive_ctem;

const FINISHED = new Set(["completed", "partial"]);
const RUNNING = new Set(["queued", "running"]);
const PAGE_SIZE = 30;

function riskOf(scan: ScanHistoryItem) {
  const score = Math.min(100, scan.critical_count * 25 + scan.high_count * 15 + scan.medium_count * 5 + scan.low_count);
  if (score >= 70) return { score, label: "High", className: "border-brand-alert/40 bg-brand-alert/10 text-brand-alert" };
  if (score >= 40) return { score, label: "Medium", className: "border-brand-yellow/40 bg-brand-yellow/10 text-brand-yellow" };
  return { score, label: "Low", className: "border-brand-success/40 bg-brand-success/10 text-brand-success" };
}

function dayLabel(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  return formatDateWithYear(iso);
}

const timeOf = (iso: string) => new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

function riskDeltas(scans: ScanHistoryItem[]): Map<string, number> {
  const deltas = new Map<string, number>();
  const lastSeen = new Map<string, number>();
  [...scans]
    .filter(scan => FINISHED.has(scan.status))
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
    .forEach(scan => {
      const key = `${scan.domain.toLowerCase()}|${scan.scan_type}`;
      const score = riskOf(scan).score;
      const previous = lastSeen.get(key);
      if (previous !== undefined) deltas.set(scan.id, score - previous);
      lastSeen.set(key, score);
    });
  return deltas;
}

function StatusNote({ scan }: { scan: ScanHistoryItem }) {
  if (RUNNING.has(scan.status)) {
    return (
      <span className="flex w-28 flex-col gap-1">
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-brand-cyan">
          <Loader2 className="size-3 animate-spin" />
          {scan.status === "queued" ? "Queued" : `Running · ${scan.progress}%`}
        </span>
        <span className="h-1 overflow-hidden rounded-full bg-white/5">
          <span className="block h-full rounded-full bg-brand-cyan" style={{ width: `${scan.progress}%` }} />
        </span>
      </span>
    );
  }
  if (scan.status === "failed") {
    return <span className="inline-flex items-center gap-1 rounded-full border border-brand-alert/40 bg-brand-alert/10 px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap text-brand-alert"><AlertTriangle className="size-3" />Failed</span>;
  }
  if (scan.status === "partial") {
    return <span className="inline-flex items-center gap-1 rounded-full border border-brand-yellow/40 bg-brand-yellow/10 px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap text-brand-yellow" title="Some sources didn't finish"><AlertTriangle className="size-3" />Partial</span>;
  }
  return null;
}

function DomainPicker({ domains, verified, value, onChange }: {
  domains: { name: string; count: number }[];
  verified: Set<string>;
  value: string;
  onChange: (domain: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", onKey); };
  }, [open]);
  const pick = (domain: string) => { onChange(domain); setOpen(false); };
  const itemClass = "flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-foreground hover:bg-white/5";
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen(prev => !prev)}
        className={cn(
          "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
          value ? "bg-white/10 text-foreground" : "text-muted-foreground hover:text-foreground"
        )}
      >
        <Globe className="size-3.5" />
        <span className="max-w-48 truncate">{value || "Domain"}</span>
        <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div role="menu" className="absolute top-full left-0 z-20 mt-1 max-h-72 w-60 overflow-y-auto rounded-lg border border-brand-panel-border bg-[#0b1625] py-1 shadow-[0_12px_32px_rgba(0,0,0,0.5)]">
          <button type="button" role="menuitemradio" aria-checked={!value} onClick={() => pick("")} className={itemClass}>
            <Globe className="size-4 text-muted-foreground" />
            <span className="flex-1">All domains</span>
            {!value && <Check className="size-4 text-brand-cyan" />}
          </button>
          <div className="my-1 border-t border-brand-panel-border" />
          {domains.map(domain => {
            const isVerified = verified.has(domain.name);
            return (
            <button key={domain.name} type="button" role="menuitemradio" aria-checked={value === domain.name} onClick={() => pick(domain.name)} className={itemClass}>
              {isVerified
                ? <ShieldCheck className="size-4 text-brand-cyan" />
                : <Satellite className="size-4 text-[#a78bfa]" />}
              <span className="flex min-w-0 flex-1 items-center gap-1.5">
                <span className="truncate">{domain.name}</span>
                {isVerified && <CheckCircle2 aria-label="Verified" className="size-3.5 shrink-0 text-brand-success" />}
              </span>
              <span className="text-[11px] text-muted-foreground">{domain.count}</span>
              {value === domain.name && <Check className="size-4 text-brand-cyan" />}
            </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function RowActions({ scan, onEmail }: { scan: ScanHistoryItem; onEmail: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", onKey); };
  }, [open]);
  const finished = FINISHED.has(scan.status);
  const running = RUNNING.has(scan.status);
  const itemClass = "flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-foreground no-underline hover:bg-white/5";
  return (
    <div ref={ref} className="relative flex" onClick={e => e.stopPropagation()}>
      <div className="flex h-9 overflow-hidden rounded-lg border border-brand-cyan/30 bg-brand-cyan/[0.06] text-brand-cyan transition-colors hover:border-brand-cyan/60">
        {finished && (
          <a
            href={getReportPdfUrl(scan.id)}
            download
            aria-label={`Download the ${scan.domain} report (PDF)`}
            title="Download report"
            className="inline-flex items-center gap-1.5 px-3 text-sm font-medium text-brand-cyan no-underline transition-colors hover:bg-brand-cyan/10"
          >
            <Download className="size-4" />
            <span className="text-[10px] font-semibold tracking-wide text-brand-cyan/50 uppercase">PDF</span>
          </a>
        )}
        <button
          type="button"
          aria-label={`More options for ${scan.domain}`}
          aria-haspopup="menu"
          aria-expanded={open}
          onClick={() => setOpen(prev => !prev)}
          className={cn("inline-flex w-9 items-center justify-center transition-colors hover:bg-brand-cyan/10", finished && "border-l border-brand-cyan/25")}
        >
          <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
        </button>
      </div>
      {open && (
        <div role="menu" className="absolute top-full right-0 z-20 mt-1 w-48 overflow-hidden rounded-lg border border-brand-panel-border bg-[#0b1625] py-1 shadow-[0_12px_32px_rgba(0,0,0,0.5)]">
          <a role="menuitem" href={running ? `/phase2_scan/progress?scan_id=${scan.id}` : `/phase2_scan/results/${scan.id}`} className={itemClass}>
            <FileText className="size-4 text-muted-foreground" />{running ? "View progress" : "View results"}
          </a>
          {finished && (
            <button type="button" role="menuitem" onClick={() => { setOpen(false); onEmail(); }} className={itemClass}>
              <Mail className="size-4 text-muted-foreground" />Email report
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function ScanRow({ scan, delta, showDate, verified, onOpen, onEmail }: {
  scan: ScanHistoryItem;
  verified: boolean;
  delta: number | undefined;
  showDate: boolean;
  onOpen: () => void;
  onEmail: () => void;
}) {
  const type = typeInfo(scan.scan_type);
  const TypeIcon = type.icon;
  const finished = FINISHED.has(scan.status);
  const problem = scan.status === "partial" || scan.status === "failed";
  const risk = riskOf(scan);
  return (
    <li
      role="link"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={e => { if (e.key === "Enter") onOpen(); }}
      className={cn(
        "group grid cursor-pointer grid-cols-[auto_minmax(0,1fr)_auto_auto_auto] items-center gap-4 rounded-xl border bg-brand-panel px-4 py-3 transition-colors hover:bg-white/[0.02] max-md:grid-cols-[auto_minmax(0,1fr)_auto] max-md:gap-y-2",
        scan.status === "partial" ? "border-brand-yellow/35 hover:border-brand-yellow/60"
          : scan.status === "failed" ? "border-brand-alert/35 hover:border-brand-alert/60"
          : "border-brand-panel-border hover:border-brand-cyan/30"
      )}
    >
      <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg border", type.className)} title={type.label}>
        <TypeIcon className="size-4" />
      </span>

      <span className="min-w-0">
        <span className="flex min-w-0 items-center gap-1.5">
          <span className="truncate font-medium text-foreground">{scan.domain}</span>
          {verified && <CheckCircle2 aria-label="Verified domain" className="size-2.5 shrink-0 text-brand-success" />}
        </span>
        <span className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className={cn("rounded-full border px-1.5 text-[10px] font-semibold uppercase", type.className)}>{type.short}</span>
          <span title={new Date(scan.created_at).toLocaleString("en-GB")}>{showDate ? `${formatDateWithYear(scan.created_at)}, ` : ""}{timeOf(scan.created_at)}</span>
        </span>
      </span>

      <span className="max-md:col-span-2 max-md:col-start-2">
        {RUNNING.has(scan.status) && <StatusNote scan={scan} />}
      </span>

      <span className="flex w-40 items-center justify-center max-md:w-auto max-md:col-start-3 max-md:row-start-1">
        {problem ? (
          <StatusNote scan={scan} />
        ) : finished ? (
          <span className="relative">
            {delta !== undefined && delta !== 0 && (
              <span
                className={cn("absolute top-1/2 left-full ml-2 -translate-y-1/2 text-[11px] font-semibold whitespace-nowrap", delta > 0 ? "text-brand-alert" : "text-brand-success")}
                title="Since the previous scan of this domain"
              >
                {delta > 0 ? "▲" : "▼"}{Math.abs(delta)}
              </span>
            )}
            <span className={cn("inline-block rounded-full border px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap", risk.className)}>{risk.score} · {risk.label}</span>
          </span>
        ) : <span className="text-[11px] text-muted-foreground">—</span>}
      </span>

      <span className="max-md:col-start-3 max-md:row-start-2 max-md:justify-self-end">
        <RowActions scan={scan} onEmail={onEmail} />
      </span>
    </li>
  );
}

export default function HistoryPage() {
  const router = useRouter();
  const [scans, setScans] = useState<ScanHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [emailScan, setEmailScan] = useState<ScanHistoryItem | null>(null);

  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [domainFilter, setDomainFilter] = useState("");
  const [verifiedDomains, setVerifiedDomains] = useState<Set<string>>(new Set());
  const [shown, setShown] = useState(PAGE_SIZE);

  useEffect(() => {
    fetch_domains({ status: "verified", limit: 100 })
      .then(result => setVerifiedDomains(new Set(result.items.map(d => d.domain.toLowerCase()))))
      .catch(() => setVerifiedDomains(new Set()));
  }, []);

  useEffect(() => {
    fetchScanHistory()
      .then(setScans)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Unknown error"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { setShown(PAGE_SIZE); }, [typeFilter, domainFilter]);

  const deltas = riskDeltas(scans);
  const domainCounts = new Map<string, number>();
  scans.forEach(s => domainCounts.set(s.domain.toLowerCase(), (domainCounts.get(s.domain.toLowerCase()) ?? 0) + 1));
  const domainOptions = [...domainCounts.entries()].map(([name, count]) => ({ name, count })).sort((a, b) => a.name.localeCompare(b.name));

  const inDomain = scans.filter(s => !domainFilter || s.domain.toLowerCase() === domainFilter);
  const typeCounts = {
    all: inDomain.length,
    active: inDomain.filter(s => typeInfo(s.scan_type).key === "active").length,
    passive: inDomain.filter(s => typeInfo(s.scan_type).key === "passive").length,
  };

  const filtered = scans
    .filter(s => !domainFilter || s.domain.toLowerCase() === domainFilter)
    .filter(s => typeFilter === "all" || typeInfo(s.scan_type).key === typeFilter)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  const visible = filtered.slice(0, shown);

  const groups: { label: string; scans: ScanHistoryItem[] }[] = [];
  visible.forEach(scan => {
    const label = dayLabel(scan.created_at);
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.scans.push(scan);
    else groups.push({ label, scans: [scan] });
  });

  const openScan = (scan: ScanHistoryItem) =>
    router.push(RUNNING.has(scan.status) ? `/phase2_scan/progress?scan_id=${scan.id}` : `/phase2_scan/results/${scan.id}`);

  return (
    <div className={styles.historyPage}>
      <NavBar />

      <section className={styles.hero}>
        <div className={styles.heroTextWrap}>
          <h1>SCAN HISTORY</h1>
        </div>
        <div className={styles.waterline} aria-hidden="true">
          <svg
            viewBox="0 0 1440 200"
            xmlns="http://www.w3.org/2000/svg"
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
            preserveAspectRatio="none"
          >
            <path d="M0,40 Q180,80 360,40 T720,40 T1080,40 T1440,40 V200 H0 Z" fill="rgba(43,180,220,0.35)" />
            <path d="M0,90 Q200,130 400,90 T800,90 T1200,90 T1440,90 V200 H0 Z" fill="rgba(15,37,75,0.9)" />
            <path d="M0,150 Q220,178 440,150 T880,150 T1320,150 T1440,150 V200 H0 Z" fill="#091628" />
          </svg>
        </div>
      </section>

      <div className={styles.content}>
        {(() => {
          if (loading) return <div className={styles.stateWrap}><p className={styles.stateText}>LOADING HISTORY...</p></div>;
          if (error) return <div className={styles.stateWrap}><p className={styles.stateText}>{error}</p></div>;
          if (scans.length === 0) return <div className={styles.stateWrap}><p className={styles.stateText}>NO SCANS YET</p></div>;
          return (
            <div className="flex w-full flex-col gap-5">
              <div className="flex flex-wrap items-center gap-3">
                <div className="inline-flex items-center rounded-lg border border-brand-panel-border bg-brand-panel-deep p-0.5">
                <div role="tablist" aria-label="Scan type" className="inline-flex">
                  {(["all", "active", "passive"] as const).map(option => (
                    <button
                      key={option}
                      type="button"
                      role="tab"
                      aria-selected={typeFilter === option}
                      onClick={() => setTypeFilter(option)}
                      className={cn(
                        "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium capitalize transition-colors",
                        typeFilter === option
                          ? option === "active" ? "bg-brand-cyan/15 text-brand-cyan" : option === "passive" ? "bg-[#a78bfa]/15 text-[#a78bfa]" : "bg-white/10 text-foreground"
                          : "text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {option === "active" && <Crosshair className="size-3.5" />}
                      {option === "passive" && <Satellite className="size-3.5" />}
                      {option}
                      <span className="rounded-full bg-white/5 px-1.5 text-[11px] text-muted-foreground">{typeCounts[option]}</span>
                    </button>
                  ))}
                </div>
                <span aria-hidden="true" className="mx-1 h-5 w-px bg-brand-panel-border" />
                <DomainPicker domains={domainOptions} verified={verifiedDomains} value={domainFilter} onChange={setDomainFilter} />
                </div>
              </div>

              {filtered.length === 0 ? (
                <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-brand-panel-border py-10 text-center">
                  <p className="text-sm text-muted-foreground">No {typeFilter === "all" ? "" : `${typeFilter} `}scans{domainFilter ? ` of ${domainFilter}` : ""} yet.</p>
                  <button type="button" onClick={() => { setTypeFilter("all"); setDomainFilter(""); }} className="text-sm font-medium text-brand-cyan hover:underline">
                    Show all scans
                  </button>
                </div>
              ) : (
                groups.map(group => (
                  <section key={group.label} className="flex flex-col gap-2">
                    {(
                      <h2 className="m-0 flex items-center gap-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase [font-family:inherit]!">
                        {group.label}
                        <span className="text-[11px] font-normal normal-case">· {group.scans.length} scan{group.scans.length === 1 ? "" : "s"}</span>
                      </h2>
                    )}
                    <ul className="m-0 flex list-none flex-col gap-2 p-0">
                      {group.scans.map(scan => (
                        <ScanRow
                          key={scan.id}
                          scan={scan}
                          delta={deltas.get(scan.id)}
                          showDate={false}
                          verified={verifiedDomains.has(scan.domain.toLowerCase())}
                          onOpen={() => openScan(scan)}
                          onEmail={() => setEmailScan(scan)}
                        />
                      ))}
                    </ul>
                  </section>
                ))
              )}

              {filtered.length > shown && (
                <button
                  type="button"
                  onClick={() => setShown(prev => prev + PAGE_SIZE)}
                  className="mx-auto inline-flex items-center gap-1.5 rounded-lg border border-brand-panel-border px-4 py-2 text-sm font-medium text-foreground hover:bg-white/5"
                >
                  Show more <span className="text-muted-foreground">({filtered.length - shown} left)</span>
                  <ChevronDown className="size-4" />
                </button>
              )}
            </div>
          );
        })()}
      </div>

      {emailScan && (
        <EmailReportDialog scanId={emailScan.id} domain={emailScan.domain} onClose={() => setEmailScan(null)} />
      )}
    </div>
  );
}