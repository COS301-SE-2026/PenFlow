"use client";
import Link from "next/link";
import type {ReactNode} from "react";
import { validateDomain } from "@/lib/domainValidator";
import { Fragment, useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { AlertTriangle, ArrowUpDown, Check, CheckCircle2, ChevronDown, Clock, Copy, Globe, Info, KeyRound, Plus, Radar,
    Search, ShieldCheck, Trash2, X, XCircle,
} from "lucide-react";

import type {LucideIcon} from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { add_domain, delete_domain, fetch_domains, verify_domain, verification_code_message,
    type domain_counts,
    type domain_item,
    type domain_pagination,
    type domain_sort_field,
    type domain_verification_status,
    type sort_order,
 } from "@/lib/domainServices";
import { Button } from "@/shared/components/ui/button";
import { Separator } from "@/shared/components/ui/separator";
import PageHero from "@/shared/components/PageHero";
import { DETAIL_SHEET_BODY_CLASS_NAME, DETAIL_SHEET_CLASS_NAME, DetailSheetBackdrop, PhoneSheetBackdrop } from "@/shared/components/DetailSheet";
import { formatDateWithYear, formatEnumLabel } from "@/lib/engagementFormat";

 const PAGE_SIZE = 20;
 const sort_options: { value: string; label: string; sort: domain_sort_field; order: sort_order }[] = [
    {value: "recent", label: "Sort: Recently Added", sort: "created_at", order: "desc" },
    {value: "az", label: "Sort: A - Z", sort: "domain", order: "asc" },
    {value: "status", label: "Sort: Status", sort: "status", order: "asc" },

 ];

 const tab_defs: { key: "all" | domain_verification_status; label: string } [] = [
    { key: "all", label: "All Domains"},
    { key: "verified", label: "Verified"},
    { key: "pending", label: "Pending"},
    { key: "failed", label: "Failed"},
    { key: "expired", label: "Expired"},
 ];

 const status_config: Record<domain_verification_status, { label: string; className: string; icon: LucideIcon}> = {
    verified: {label: "Verified", className: "border-brand-success text-brand-success bg-brand-success/10", icon: CheckCircle2 },
    pending: {label: "Pending", className: "border-brand-yellow text-brand-yellow bg-brand-yellow/10", icon: Clock },
    failed: {label: "Failed", className: "border-brand-alert text-brand-alert bg-brand-alert/10", icon: XCircle },
    expired: {label: "Expired", className: "border-brand-orange text-brand-orange bg-brand-orange/10", icon: AlertTriangle },
 };
 
 function format_timestamp(iso: string): string {
   return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
   });
 }

 const RING_COLOR: Record<domain_verification_status, string> = {
    verified: "var(--color-brand-success)",
    pending: "var(--color-brand-yellow)",
    failed: "var(--color-brand-alert)",
    expired: "var(--color-brand-orange)",
 };

 const status_accent: Record<domain_verification_status, { text: string; count: string; dot: string; edge: string; glow: string }> = {
    verified: { text: "text-brand-success", count: "bg-brand-success/15 text-brand-success", dot: "bg-brand-success", edge: "shadow-[inset_3px_0_0_var(--color-brand-success)]", glow: "shadow-[0_0_8px_var(--color-brand-success)]" },
    pending: { text: "text-brand-yellow", count: "bg-brand-yellow/15 text-brand-yellow", dot: "bg-brand-yellow", edge: "shadow-[inset_3px_0_0_var(--color-brand-yellow)]", glow: "shadow-[0_0_8px_var(--color-brand-yellow)]" },
    failed: { text: "text-brand-alert", count: "bg-brand-alert/15 text-brand-alert", dot: "bg-brand-alert", edge: "shadow-[inset_3px_0_0_var(--color-brand-alert)]", glow: "shadow-[0_0_8px_var(--color-brand-alert)]" },
    expired: { text: "text-brand-orange", count: "bg-brand-orange/15 text-brand-orange", dot: "bg-brand-orange", edge: "shadow-[inset_3px_0_0_var(--color-brand-orange)]", glow: "shadow-[0_0_8px_var(--color-brand-orange)]" },
 };

 function StatusBadge({ status }: {status: domain_verification_status}) {
   const { label, className } = status_config[status];
   const accent = status_accent[status];
   return (
      <Badge variant = "outline" className={cn("gap-1.5 border-transparent uppercase tracking-wide", className)}>
         <span className = {cn("size-1.5 rounded-full", accent.dot, accent.glow)} />
         {label}
      </Badge>
   );
 }

 const TILE_CLASSES: Record<domain_verification_status, string> = {
    verified: "bg-brand-success/15 text-brand-success border-brand-success/30",
    pending: "bg-brand-yellow/15 text-brand-yellow border-brand-yellow/30",
    failed: "bg-brand-alert/15 text-brand-alert border-brand-alert/30",
    expired: "bg-brand-orange/15 text-brand-orange border-brand-orange/30",
 };

 function DomainTile({ status, className }: { status: domain_verification_status; className?: string }) {
   return (
      <span aria-hidden = "true" className = {cn("flex size-8 shrink-0 items-center justify-center rounded-lg border", TILE_CLASSES[status], className)}>
         <Globe className = "size-4" />
      </span>
   );
 }

 const METHOD_LABELS: Record<string, string> = {
    dns_txt: "DNS TXT record",
    dns: "DNS TXT record",
    http_file: "HTTP file",
    meta_tag: "HTML meta tag",
 };
 function method_label(method: string): string {
   return METHOD_LABELS[method.toLowerCase()] ?? formatEnumLabel(method);
 }

 function RecordField({ label, value, display }: { label: string; value: string; display?: string }) {
   const [copied, set_copied] = useState(false);

   async function handle_copy() {
      try {
         await navigator.clipboard.writeText(value);
         set_copied(true);
         setTimeout(() => set_copied(false), 1500);
      } catch {}
   }

   return (
      <div className = "flex items-start gap-2 rounded-md border border-brand-panel-border bg-brand-panel-deep px-2.5 py-1.5">
         <span className = "w-11 shrink-0 pt-0.5 text-[11px] text-muted-foreground uppercase">{label}</span>
         <code className = "min-w-0 flex-1 font-mono text-xs leading-5 break-all text-foreground">{display ?? value}</code>
         <button
            type = "button"
            onClick = {(e) => { e.stopPropagation(); void handle_copy(); }}
            aria-label = {`Copy ${label.toLowerCase()}`}
            className = "shrink-0 pt-0.5 text-muted-foreground transition-colors hover:text-brand-cyan"
         >
            {copied ? <Check className = "size-3.5 text-brand-success" /> : <Copy className = "size-3.5" />}
         </button>
      </div>
   );
 }

 function DnsRecord({ token }: { token: string }) {
   return (
      <div className = "flex flex-col gap-1.5">
         <div className = "grid grid-cols-2 gap-1.5">
            <RecordField label = "Type" value = "TXT" />
            <RecordField label = "Name" value = "@" display = "@ (root)" />
         </div>
         <RecordField label = "Value" value = {token} />
      </div>
   );
 }

 type verify_feedback = { kind: "success" | "error"; message: string };

 function VerifyStatus({ domain, feedback }: { domain: domain_item; feedback?: verify_feedback }) {
   let tone: "neutral" | "error" | "success";
   let title: string;
   let detail: string;
   if (feedback?.kind === "success" || domain.status === "verified") {
      tone = "success"; title = "Verified"; detail = "Active scans are now unlocked.";
   } else if (feedback?.kind === "error") {
      tone = "error"; title = feedback.message; detail = "Please try again in a few minutes.";
   } else if (!domain.last_checked_at) {
      tone = "neutral"; title = "Not checked yet"; detail = "Press Verify once the TXT record is in place.";
   } else {
      tone = "error";
      title = domain.last_verification_code ? verification_code_message[domain.last_verification_code] : "Verification failed.";
      detail = `Last checked ${format_timestamp(domain.last_checked_at)}.${domain.last_verification_code === "record_not_found" ? " DNS can take a while, so try again shortly." : ""}`;
   }
   const Icon = tone === "success" ? CheckCircle2 : tone === "error" ? AlertTriangle : Info;
   return (
      <div className = {cn(
         "flex gap-2.5 rounded-lg border p-3",
         tone === "neutral" && "border-brand-panel-border bg-white/[0.02]",
         tone === "error" && "border-brand-alert/25 bg-brand-alert/5",
         tone === "success" && "border-brand-success/30 bg-brand-success/10"
      )}>
         <Icon className = {cn("mt-0.5 size-4 shrink-0", tone === "neutral" && "text-[#94a3b8]", tone === "error" && "text-brand-alert", tone === "success" && "text-brand-success")} />
         <div className = "min-w-0">
            <p className = "text-sm font-medium text-foreground">{title}</p>
            <p className = "mt-0.5 text-xs text-muted-foreground">{detail}</p>
         </div>
      </div>
   );
 }

 function VerifyButton({ domain, verifying, on_verify, className }: { domain: domain_item; verifying: boolean; on_verify: (id: string) => void; className?: string }) {
   return (
      <Button
         className = {cn("bg-brand-yellow text-black hover:bg-brand-yellow/85", className)}
         disabled = {verifying}
         onClick = {(e) => { e.stopPropagation(); on_verify(domain.id); }}
      >
         <ShieldCheck className = "size-4" />
         {verifying ? "Verifying..." : domain.status === "pending" ? "Verify now" : "Retry verification"}
      </Button>
   );
 }

 function SectionLabel({ children }: { children: ReactNode }) {
   return <h3 className = "text-xs font-semibold tracking-wide text-muted-foreground uppercase [font-family:inherit]!">{children}</h3>;
 }

 function Meta({ label, value }: { label: string; value: string }) {
   return (
      <div className = "min-w-0">
         <p className = "text-xs text-muted-foreground">{label}</p>
         <p className = "text-sm text-foreground">{value}</p>
      </div>
   );
 }

 function VerifiedActions({ domain, className }: { domain: domain_item; className?: string }) {
   return (
      <Button asChild className = {cn("gap-2", className)}>
         <Link href = {`/domains/${domain.id}/brand-intelligence?domain=${encodeURIComponent(domain.domain)}`} onClick = {(e) => e.stopPropagation()}>
            <Radar className = "size-4" />
            Brand Intelligence
         </Link>
      </Button>
   );
 }

 function DeleteButton({ domain, on_delete }: { domain: domain_item; on_delete: (id: string) => void }) {
   return (
      <button
         type = "button"
         onClick = {(e) => { e.stopPropagation(); on_delete(domain.id); }}
         className = "inline-flex items-center gap-1.5 rounded-md px-1 py-1 text-xs text-brand-alert transition-colors hover:text-brand-alert/80"
      >
         <Trash2 className = "size-3.5" />
         Delete domain
      </button>
   );
 }

 const UNVERIFIED_COLUMNS = "grid-cols-[4fr_5fr_5fr]";
 const UNVERIFIED_RATIOS = [5 / 4, 1];

 type verify_phase = "idle" | "checking" | "failed" | "success" | "verified";
 type progress_tone = "done" | "current" | "checking" | "next";

 const PULSE_MS = 1600;
 const FAIL_SHORT: Record<string, string> = {
    record_not_found: "Record not found",
    token_mismatch: "Token didn't match",
    lookup_failed: "DNS lookup failed",
 };

 function ProgressCircle({ icon: Icon, tone, failed }: { icon: LucideIcon; tone: progress_tone; failed?: boolean }) {
   return (
      <span className = {cn(
         "flex size-7 shrink-0 items-center justify-center rounded-full border transition-colors duration-500",
         tone === "done" && "border-brand-success/50 bg-brand-success/15 text-brand-success",
         tone === "current" && "border-brand-cyan/60 bg-brand-cyan/15 text-brand-cyan shadow-[0_0_12px_-2px_rgba(43,216,245,0.5)]",
         tone === "checking" && "border-brand-yellow/70 bg-brand-yellow/15 text-brand-yellow shadow-[0_0_12px_-2px_rgba(250,204,21,0.6)]",
         tone === "next" && "border-[#475569] text-[#94a3b8]",
         failed && "step-flash-fail"
      )}>
         {tone === "done" ? <Check className = "size-3.5" /> : <Icon className = "size-3.5" />}
      </span>
   );
 }

 type line_tone = "green" | "cyan" | "yellow";
 const LINE_BASE: Record<line_tone, string> = { green: "bg-brand-success/70", cyan: "bg-brand-cyan/25", yellow: "bg-brand-yellow/30" };
 const LINE_PULSE: Record<line_tone, string> = { green: "via-brand-success", cyan: "via-brand-cyan", yellow: "via-brand-yellow" };

 function ProgressLine({ tone, pulse, vertical, className }: { tone: line_tone; pulse?: "loop" | "once"; vertical?: boolean; className?: string }) {
   return (
      <span aria-hidden = "true" className = {cn(
         "relative overflow-hidden rounded transition-colors duration-500",
         vertical ? "my-1 min-h-3 w-0.5 flex-1" : "h-0.5 flex-1",
         LINE_BASE[tone],
         className
      )}>
         {pulse && (
            <span
               key = {`${tone}-${pulse}`}
               className = {cn(
                  "absolute from-transparent to-transparent motion-reduce:hidden",
                  vertical ? "inset-x-0 top-0 h-2/5 bg-gradient-to-b" : "inset-y-0 left-0 w-2/5 bg-gradient-to-r",
                  LINE_PULSE[tone]
               )}
               style = {{ animation: `${vertical ? "step-flow-y" : "step-flow-x"} ${PULSE_MS}ms ease-in-out ${pulse === "loop" ? "infinite" : "1 forwards"}` }}
            />
         )}
      </span>
   );
 }

 function DomainProgress({ phase, reason, vertical = false, columns = "grid-cols-3", ratios = [1, 1] }: { phase: verify_phase; reason?: string; vertical?: boolean; columns?: string; ratios?: number[] }) {
   const dns_done = phase === "success" || phase === "verified";
   const steps: { icon: LucideIcon; title: string; hint: string; tone: progress_tone; failed?: boolean }[] = [
      { icon: Globe, title: "Add domain", hint: "Done", tone: "done" },
      {
         icon: KeyRound, title: "DNS record",
         hint: dns_done ? "Record found" : phase === "checking" ? "Looking it up..." : "Add a TXT record",
         tone: dns_done ? "done" : phase === "checking" ? "checking" : "current",
      },
      {
         icon: ShieldCheck, title: "Verify",
         hint: dns_done ? "Active scans unlocked" : phase === "checking" ? "Checking DNS..." : phase === "failed" ? (reason ?? "Verification failed") : "Unlocks active scans",
         tone: dns_done ? "done" : "next",
         failed: phase === "failed",
      },
   ];
   const lines: { tone: line_tone; pulse?: "loop" | "once" }[] = [
      { tone: "green" },
      dns_done ? { tone: "green", pulse: phase === "success" ? "once" : undefined }
         : phase === "checking" ? { tone: "yellow", pulse: "loop" }
         : { tone: "cyan", pulse: "loop" },
   ];
   const text = (step: typeof steps[number], index: number) => (
      <span className = "flex min-w-0 flex-col">
         <span className = {cn("text-xs font-medium transition-colors",
            step.failed ? "text-brand-alert" : step.tone === "done" ? "text-brand-success" : step.tone === "next" ? "text-[#cbd5e1]" : "text-foreground")}>
            {index + 1}. {step.title}
         </span>
         <span className = {cn("text-[11px]", step.failed ? "text-brand-alert/80" : step.tone === "checking" || (index === 2 && phase === "checking") ? "text-brand-yellow" : "text-[#94a3b8]")}>
            {step.hint}
         </span>
      </span>
   );
   return (
      <nav aria-label = "Domain verification progress" aria-live = "polite">
         {vertical ? (
            <ol className = "flex flex-col">
               {steps.map((step, index) => (
                  <li key = {step.title} className = "flex gap-3">
                     <span className = "flex flex-col items-center">
                        <ProgressCircle icon = {step.icon} tone = {step.tone} failed = {step.failed} />
                        {index < lines.length && <ProgressLine {...lines[index]} vertical />}
                     </span>
                     <span className = "pt-0.5 pb-2">{text(step, index)}</span>
                  </li>
               ))}
            </ol>
         ) : (
            <ol className = {cn("grid gap-3", columns)}>
               {steps.map((step, index) => (
                  <li key = {step.title} className = "relative flex flex-col items-center gap-2 text-center">
                     <ProgressCircle icon = {step.icon} tone = {step.tone} failed = {step.failed} />
                     {index < lines.length && (
                        <span className = "absolute top-[13px] left-[calc(50%+18px)] flex" style = {{ width: `calc(${50 + 50 * ratios[index]}% + 12px - 36px)` }}>
                           <ProgressLine {...lines[index]} />
                        </span>
                     )}
                     {text(step, index)}
                  </li>
               ))}
            </ol>
         )}
      </nav>
   );
 }

 function fail_reason(domain: domain_item, feedback?: verify_feedback): string | undefined {
   if (feedback?.kind === "error") return "Check failed";
   return domain.last_verification_code ? FAIL_SHORT[domain.last_verification_code] : undefined;
 }

 function DomainExpansion({ domain, phase, verifying, feedback, on_verify, on_delete }: {
   domain: domain_item;
   phase: verify_phase;
   verifying: boolean;
   feedback?: verify_feedback;
   on_verify: (id: string) => void;
   on_delete: (id: string) => void;
 }) {
   const verified = domain.status === "verified";
   return (
      <div className = "flex animate-in flex-col gap-4 rounded-b-lg border-t border-brand-cyan/15 bg-brand-panel-deep/60 px-5 py-4 shadow-[inset_3px_0_0_var(--ring),inset_-1px_0_0_var(--ring),inset_0_-1px_0_var(--ring)] duration-200 fade-in slide-in-from-top-1" onClick = {(e) => e.stopPropagation()}>
         <DomainProgress phase = {phase} reason = {fail_reason(domain, feedback)} columns = {verified ? "grid-cols-3" : UNVERIFIED_COLUMNS} ratios = {verified ? [1, 1] : UNVERIFIED_RATIOS} />
         {verified ? (
            <div className = "flex flex-col gap-4 rounded-lg border border-brand-success/20 bg-brand-panel p-4">
               <div className = "flex items-center gap-4">
                  <div className = "grid flex-1 grid-cols-3 gap-3">
                     <Meta label = "Added" value = {format_timestamp(domain.created_at)} />
                     <Meta label = "Verified" value = {domain.verified_at ? format_timestamp(domain.verified_at) : "—"} />
                     <Meta label = "Last checked" value = {domain.last_checked_at ? format_timestamp(domain.last_checked_at) : "Never"} />
                  </div>
                  <VerifiedActions domain = {domain} className = "shrink-0 px-6" />
               </div>
               {feedback?.kind === "success" && <VerifyStatus domain = {domain} feedback = {feedback} />}
            </div>
         ) : (
            <>
               <div className = {cn("grid items-start gap-3", UNVERIFIED_COLUMNS)}>
                  <div className = "flex flex-col gap-2 rounded-lg border border-brand-success/20 bg-brand-success/[0.04] p-3">
                     <p className = "flex items-center gap-1.5 text-sm font-medium text-brand-success"><CheckCircle2 className = "size-4" /> Domain added</p>
                     <Meta label = "Added" value = {format_timestamp(domain.created_at)} />
                     <Meta label = "Method" value = {method_label(domain.verification_method)} />
                  </div>
                  <div className = "flex flex-col gap-2 rounded-lg border border-brand-cyan/30 bg-brand-panel p-3">
                     <p className = "text-sm font-medium text-foreground">Add this TXT record at your DNS provider</p>
                     <DnsRecord token = {domain.verification_token} />
                     <p className = "text-xs text-muted-foreground">DNS changes usually show up within minutes, but can take up to 24 hours.</p>
                  </div>
                  <div className = "flex flex-col gap-3 rounded-lg border border-brand-panel-border bg-brand-panel p-3">
                     <p className = "text-sm font-medium text-foreground">Check the record</p>
                     <VerifyStatus domain = {domain} feedback = {feedback} />
                     <VerifyButton domain = {domain} verifying = {verifying} on_verify = {on_verify} className = "w-full" />
                  </div>
               </div>
            </>
         )}
         <div className = "flex items-center justify-between gap-3 border-t border-brand-panel-border pt-3 text-xs text-muted-foreground">
            <span>
               Added {format_timestamp(domain.created_at)} · Last checked {domain.last_checked_at ? format_timestamp(domain.last_checked_at) : "never"}
            </span>
            <DeleteButton domain = {domain} on_delete = {on_delete} />
         </div>
      </div>
   );
 }

 function DomainDetailPanel ({
   domain, phase, on_close, on_verify, on_delete, verifying, feedback,
 }: {
   domain:domain_item;
   phase: verify_phase;
   on_close: () => void;
   on_verify: (id: string) => void;
   on_delete: (id:string) => void;
   verifying: boolean;
   feedback?: verify_feedback;
 }) {
   const verified = domain.status === "verified";
   return (
      <Card className = {cn("border border-brand-panel-border bg-brand-panel ring-0", DETAIL_SHEET_CLASS_NAME)}>
         <CardContent className = {cn("flex flex-col gap-5 overflow-y-auto", DETAIL_SHEET_BODY_CLASS_NAME)}>
            <div className = "flex items-start justify-between gap-3">
               <div className = "flex min-w-0 items-center gap-2.5">
                  <DomainTile status = {domain.status} />
                  <div className = "min-w-0">
                     <h2 className = "text-base font-semibold break-all text-foreground [font-family:inherit]! tracking-normal!">{domain.domain}</h2>
                     <StatusBadge status = {domain.status} />
                  </div>
               </div>
               <button
                  type = "button"
                  onClick = {on_close}
                  aria-label = "Close domain details"
                  className = "shrink-0 text-muted-foreground transition-colors hover:text-foreground"
               >
                  <X className = "size-5"/>
               </button>
            </div>

            <DomainProgress phase = {phase} reason = {fail_reason(domain, feedback)} vertical />
            {verified ? (
               <>
                  <div className = "grid grid-cols-2 gap-x-4 gap-y-3">
                     <Meta label = "Added" value = {format_timestamp(domain.created_at)} />
                     <Meta label = "Verified" value = {domain.verified_at ? format_timestamp(domain.verified_at) : "—"} />
                  </div>
                  {feedback?.kind === "success" && <VerifyStatus domain = {domain} feedback = {feedback} />}
                  <VerifiedActions domain = {domain} className = "h-11 w-full" />
               </>
            ) : (
               <>
                  <div className = "flex flex-col gap-2">
                     <SectionLabel>Add this TXT record</SectionLabel>
                     <DnsRecord token = {domain.verification_token} />
                     <p className = "text-xs text-muted-foreground">DNS changes usually show up within minutes, but can take up to 24 hours.</p>
                  </div>
                  <div className = "flex flex-col gap-2">
                     <SectionLabel>Status</SectionLabel>
                     <VerifyStatus domain = {domain} feedback = {feedback} />
                  </div>
                  <VerifyButton domain = {domain} verifying = {verifying} on_verify = {on_verify} className = "h-11 w-full" />
               </>
            )}

            <div className = "flex items-center justify-between gap-3 border-t border-brand-panel-border pt-3 text-xs text-muted-foreground">
               <span>Last checked {domain.last_checked_at ? format_timestamp(domain.last_checked_at) : "never"}</span>
               <DeleteButton domain = {domain} on_delete = {on_delete} />
            </div>
         </CardContent>
      </Card>
   );
 }

 const NARROW_QUERY = "(max-width: 767px)";
 function subscribe_narrow(callback: () => void) {
   const query = window.matchMedia(NARROW_QUERY);
   query.addEventListener("change", callback);
   return () => query.removeEventListener("change", callback);
 }
 function useIsNarrow(): boolean {
   return useSyncExternalStore(subscribe_narrow, () => window.matchMedia(NARROW_QUERY).matches, () => false);
 }

const ADD_STEPS: { title: string; hint: string; icon: LucideIcon }[] = [
   { title: "Add domain", hint: "Enter it below", icon: Globe },
   { title: "DNS record", hint: "Add a TXT record", icon: KeyRound },
   { title: "Verify", hint: "Unlocks active scans", icon: ShieldCheck },
];

function step_state(index: number, current: number) {
   return index < current ? "done" : index === current ? "current" : "next";
}

function StepCircle({ index, current }: { index: number; current: number }) {
   const state = step_state(index, current);
   const Icon = ADD_STEPS[index].icon;
   return (
      <span className = {cn(
         "flex size-7 shrink-0 items-center justify-center rounded-full border transition-colors",
         state === "done" && "border-brand-success/50 bg-brand-success/15 text-brand-success",
         state === "current" && "border-brand-cyan/60 bg-brand-cyan/15 text-brand-cyan shadow-[0_0_12px_-2px_rgba(43,216,245,0.5)]",
         state === "next" && "border-[#475569] text-[#94a3b8]"
      )}>
         {state === "done" ? <Check className = "size-3.5" /> : <Icon className = "size-3.5" />}
      </span>
   );
}

function StepText({ index, current }: { index: number; current: number }) {
   const state = step_state(index, current);
   return (
      <span className = "flex min-w-0 flex-col">
         <span className = {cn("text-xs font-medium", state === "next" ? "text-[#cbd5e1]" : state === "done" ? "text-brand-success" : "text-foreground")}>
            {index + 1}. {ADD_STEPS[index].title}
         </span>
         <span className = "text-[11px] text-[#94a3b8]">{state === "done" ? "Done" : ADD_STEPS[index].hint}</span>
      </span>
   );
}

function StepLine({ index, current, vertical = false, ahead = false }: { index: number; current: number; vertical?: boolean; ahead?: boolean }) {
   const done = index < current;
   const leading = ahead ? index === current : index === current - 1;
   return (
      <span aria-hidden = "true" className = {cn(
         "relative overflow-hidden rounded",
         vertical ? "my-1 min-h-3 w-px flex-1" : "h-px flex-1",
         done ? (ahead ? "bg-brand-success/70" : "bg-brand-cyan/50") : leading && ahead ? "bg-brand-cyan/25" : "bg-[#334155]",
         leading && (vertical ? "w-0.5" : "h-0.5")
      )}>
         {leading && (
            <span
               className = {cn(
                  "absolute motion-reduce:hidden",
                  vertical
                     ? "inset-x-0 top-0 h-2/5 bg-gradient-to-b from-transparent via-brand-cyan to-transparent"
                     : "inset-y-0 left-0 w-2/5 bg-gradient-to-r from-transparent via-brand-cyan to-transparent"
               )}
               style = {{ animation: `${vertical ? "step-flow-y" : "step-flow-x"} 1.6s ease-in-out infinite` }}
            />
         )}
      </span>
   );
}

function AddDomainSteps({ current, vertical = false, ahead = false }: { current: number; vertical?: boolean; ahead?: boolean }) {
   const horizontal = (
      <ol className = {cn("grid grid-cols-3 gap-3", "max-sm:hidden")}>
         {ADD_STEPS.map((step, index) => (
            <li key = {step.title} className = "flex flex-col gap-2">
               <span className = "flex items-center gap-2">
                  <StepCircle index = {index} current = {current} />
                  {index < ADD_STEPS.length - 1 && <StepLine index = {index} current = {current} ahead = {ahead} />}
               </span>
               <StepText index = {index} current = {current} />
            </li>
         ))}
      </ol>
   );
   const vertical_list = (
      <ol className = {cn("flex flex-col", !vertical && "hidden max-sm:flex")}>
         {ADD_STEPS.map((step, index) => (
            <li key = {step.title} className = "flex gap-3">
               <span className = "flex flex-col items-center">
                  <StepCircle index = {index} current = {current} />
                  {index < ADD_STEPS.length - 1 && <StepLine index = {index} current = {current} vertical ahead = {ahead} />}
               </span>
               <span className = "pt-0.5 pb-2"><StepText index = {index} current = {current} /></span>
            </li>
         ))}
      </ol>
   );
   return (
      <nav aria-label = {`Domain setup: step ${current + 1} of ${ADD_STEPS.length}`}>
         {!vertical && horizontal}
         {vertical_list}
      </nav>
   );
}

function AddDomainForm({
   on_cancel,
   on_added,
   existing_domains,
}: {
   on_cancel: () => void;
   on_added: (id: string) => void;
   existing_domains: string[];
}) {
const [domain_name, set_domain_name] = useState("");
const [submitting, set_submitting] = useState(false);
const [form_error, set_form_error] = useState<string | null>(null);

const trimmed = domain_name.trim();
const validation = trimmed ? validateDomain(trimmed) : null;
const duplicate = validation?.valid === true && existing_domains.includes(validation.domain);
const live_error = validation && !validation.valid ? validation.error : duplicate ? "Already added" : null;
const cleaned = validation?.valid && !duplicate && validation.domain !== trimmed.toLowerCase() ? validation.domain : null;
const can_add = validation?.valid === true && !duplicate && !submitting;

useEffect(() => {
   const on_key = (e: KeyboardEvent) => { if (e.key === "Escape" && !submitting) on_cancel(); };
   window.addEventListener("keydown", on_key);
   return () => window.removeEventListener("keydown", on_key);
}, [on_cancel, submitting]);

async function handle_add() {
   if (!can_add || !validation?.valid) return;
   set_submitting(true);
   set_form_error(null);
   try {
      const added = await add_domain(validation.domain);
      on_added(added.id);
   } catch (err) {
      set_form_error(err instanceof Error ? err.message : "Failed to add domain");
   } finally {
      set_submitting(false);
   }
}

const message = form_error ?? live_error;

return (
   <>
   <PhoneSheetBackdrop onClose={on_cancel} label="Close add domain" />
   <Card className = "border border-brand-cyan/30 bg-gradient-to-br from-brand-panel to-brand-panel-deep ring-0 max-sm:fixed max-sm:inset-x-0 max-sm:bottom-0 max-sm:z-50 max-sm:max-h-[85dvh] max-sm:overflow-y-auto max-sm:rounded-b-none max-sm:border-b-0 max-sm:pb-[env(safe-area-inset-bottom)] max-sm:shadow-[0_-12px_40px_rgb(0_0_0/0.5)]">
      <CardContent className = "flex flex-col gap-4">
         <div className = "flex items-start justify-between gap-3">
            <div className = "flex items-center gap-2.5">
               <span className = "flex size-8 items-center justify-center rounded-lg border border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan">
                  <Globe className = "size-4"/>
               </span>
               <h2 className = "text-sm font-semibold uppercase tracking-wide text-foreground [font-family:inherit]!">Add Domain</h2>
            </div>
            <button
               type = "button"
               onClick = {on_cancel}
               disabled = {submitting}
               aria-label = "Close add domain"
               className = "rounded-md p-1 text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground"
            >
               <X className = "size-4" />
            </button>
         </div>

         <div className = "w-full sm:mx-auto sm:max-w-[740px]">
            <AddDomainSteps current = {can_add ? 1 : 0} />
         </div>

         <Separator className = "bg-brand-panel-border"/>
         <div className = "flex flex-col gap-1.5 sm:mx-auto sm:w-fit sm:max-w-full">
            <Label htmlFor="new-domain">Domain</Label>
            <div className = "flex items-start gap-2 max-sm:flex-col max-sm:items-stretch">
               <div className = "relative w-full sm:w-[520px] sm:max-w-[calc(100vw-22rem)]">
                  <Globe className = "absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"/>
                  <Input
                     id = "new-domain"
                     placeholder="example.com"
                     value={domain_name}
                     onChange = {(e) => { set_domain_name(e.target.value); set_form_error(null); }}
                     onKeyDown = {(e) => {
                        if (e.key === "Enter") void handle_add();
                     }}
                     inputMode = "url"
                     autoCapitalize = "off"
                     autoCorrect = "off"
                     spellCheck = {false}
                     aria-invalid = {message ? true : undefined}
                     aria-describedby = "new-domain-hint"
                     className = {cn(
                        "h-10 border-brand-panel-border pr-9 pl-9 focus-visible:border-brand-cyan focus-visible:ring-brand-cyan/25 max-sm:h-11 max-sm:text-base",
                        message && "border-brand-alert/60 focus-visible:border-brand-alert focus-visible:ring-brand-alert/20",
                        can_add && "border-brand-success/50"
                     )}
                     autoFocus
                  />
                  {can_add && <Check aria-hidden = "true" className = "absolute top-1/2 right-3 size-4 -translate-y-1/2 text-brand-success" />}
               </div>
               <div className = "flex gap-2 max-sm:flex-col-reverse">
                  <Button variant = "outline" onClick={on_cancel} disabled={submitting} className = "h-10 max-sm:h-11">
                     Cancel
                  </Button>
                  <Button disabled={!can_add} onClick={() => void handle_add()} className = "h-10 gap-1.5 max-sm:h-11">
                     <Plus className = "size-4" />
                     {submitting ? "Adding" : "Add Domain"}
                  </Button>
               </div>
            </div>
            <p id = "new-domain-hint" className = {cn("min-h-4 text-xs", message ? "text-brand-alert" : "text-muted-foreground")}>
               {message ?? (cleaned ? <>Will add: <span className = "font-medium text-foreground">{cleaned}</span></> : "Enter the domain without https:// — pasted URLs are cleaned up for you.")}
            </p>
         </div>
      </CardContent>
   </Card>
   </>
);}

function DomainCard({
   domain, selected, on_open,
}: {
   domain: domain_item;
   selected: boolean;
   on_open: () => void;
}) {
   return (
      <button
         type = "button"
         onClick = {on_open}
         className = {cn(
            "flex w-full flex-col gap-2 rounded-xl border border-brand-panel-border bg-brand-panel p-3.5 text-left text-sm outline-none active:bg-white/[0.03] focus-visible:ring-2 focus-visible:ring-brand-cyan/50",
            status_accent[domain.status].edge,
            selected && "border-brand-cyan/40"
         )}
      >
         <span className = "flex w-full items-start justify-between gap-3">
            <span className = "flex min-w-0 items-center gap-2.5 font-medium text-foreground">
               <DomainTile status = {domain.status} />
               <span className = "flex min-w-0 flex-col">
                  <span className = "break-all">{domain.domain}</span>
                  <span className = "text-[11px] font-normal text-muted-foreground">{method_label(domain.verification_method)}</span>
               </span>
            </span>
            <span className = "shrink-0"><StatusBadge status={domain.status} /></span>
         </span>
         <span className = "text-xs text-muted-foreground">
            Added {formatDateWithYear(domain.created_at)}
         </span>
      </button>
   );
}

function useDomains() {
   const [domains, set_domains] = useState<domain_item[]>([]);
   const [counts, set_counts] = useState<domain_counts | null>(null);
   const [pagination, set_pagination] = useState<domain_pagination| null>(null);
   const [loading, set_loading] = useState(false);
   const [error, set_error] = useState<string | null>(null);

   const [active_tab, set_active_tab] = useState<"all" | domain_verification_status>("all");
   const [search, set_search] = useState("");
   const [debounced_search, set_debounced_search] = useState("");
   const [sort_value, set_sort_value] = useState("recent");
   const [verifying_id, set_verifying_id] = useState<string | null>(null);

   const request_id_ref = useRef(0);

   useEffect(()=>{
      const handle = setTimeout (() => set_debounced_search(search.trim()), 350);
      return () => clearTimeout(handle);
   }, [search]);

   const load_domains = useCallback(
      async (params: { offset: number; append: boolean}) => {
         const request_id = ++request_id_ref.current;
         set_loading(true);
         set_error(null);
         const option = sort_options.find((o) => o.value === sort_value) ?? sort_options[0];
         try{
            const result = await fetch_domains({
               status: active_tab === "all" ?undefined : active_tab,
               search: debounced_search || undefined,
               sort: option.sort,
               order: option.order,
               limit: PAGE_SIZE,
               offset: params.offset,
            });
            if (request_id_ref.current !== request_id) return;
            set_domains((prev) => (params.append ? [...prev, ...result.items] : result.items));
            set_counts(result.counts);
            set_pagination(result.pagination);
         }
         catch (err) {
            if (request_id_ref.current !== request_id) return;
            set_error(err instanceof Error ? err.message : "Failed to load domains");
         }
         finally {
            if (request_id_ref.current === request_id) set_loading(false);
         }
      },
      [active_tab, debounced_search, sort_value]
   );

   const refetch = useCallback (() => load_domains({offset:0, append: false}), [load_domains]);

   useEffect(() => {
      void refetch();
   }, [refetch]);

   function handle_load_more() {
      if (!pagination?.has_more || loading) return;
      void load_domains ({ offset: domains.length, append: true});
   }

   const [verify_feedback, set_verify_feedback] = useState<Record<string, verify_feedback>>({});

   async function verify(domain_id: string, min_pass_ms = 0): Promise<boolean> {
      const started = Date.now();
      set_verifying_id(domain_id);
      set_verify_feedback((prev) => { const next = { ...prev }; delete next[domain_id]; return next; });
      let ok = false;
      let feedback: verify_feedback | null = null;
      try { 
         const result = await verify_domain(domain_id);
         ok = result.status === "verified";
         if (ok) feedback = { kind: "success", message: "Verified" };
      } catch (err) {
         feedback = { kind: "error", message: err instanceof Error ? err.message : "Verification failed" };
      } finally {
         if (min_pass_ms > 0) {
            const elapsed = Date.now() - started;
            const wait = Math.max(1, Math.ceil(elapsed / min_pass_ms)) * min_pass_ms - elapsed;
            await new Promise((resolve) => setTimeout(resolve, wait));
         }
         const result_feedback = feedback;
         if (result_feedback) set_verify_feedback((prev) => ({ ...prev, [domain_id]: result_feedback }));
         set_verifying_id(null);
         void refetch();
      }
      return ok;
   }

   async function remove(domain_id: string): Promise<boolean> {
      try {
         await delete_domain(domain_id);
         void refetch();
         return true;
      } catch(err) {
         set_error(err instanceof Error ? err.message: "Failed to remove domain");
         return false;
      }
   }

   return{ domains, counts, pagination, loading, error, active_tab, set_active_tab, search, set_search, sort_value, set_sort_value, verifying_id, verify_feedback, refetch, handle_load_more, verify, remove,};
}

export default function DomainsHome() {
   const {
      domains, counts, pagination, loading, error, active_tab, set_active_tab, search, set_search, sort_value, set_sort_value, verifying_id, verify_feedback, refetch, handle_load_more, verify, remove,
   } = useDomains();

   const [selected_id, set_selected_id] = useState<string | null>(null);
   const [show_add_domain, set_show_add_domain] = useState(false);

   async function handle_delete(domain_id: string) {
      const deleted = await remove(domain_id);
      if(deleted) set_selected_id((prev) => (prev === domain_id ? null : prev));
   }

   const selected_domain = domains.find((d) => d.id === selected_id) ?? null;
   const is_narrow = useIsNarrow();

   const [verify_phases, set_verify_phases] = useState<Record<string, "checking" | "failed" | "success">>({});
   const set_phase = (domain_id: string, phase: "checking" | "failed" | "success" | null) =>
      set_verify_phases((prev) => {
         const next = { ...prev };
         if (phase) next[domain_id] = phase; else delete next[domain_id];
         return next;
      });
   const phase_of = (domain: domain_item): verify_phase =>
      verify_phases[domain.id] ?? (domain.status === "verified" ? "verified" : "idle");

   async function handle_verify(domain_id: string) {
      set_selected_id(domain_id);
      set_phase(domain_id, "checking");
      const ok = await verify(domain_id, PULSE_MS);
      set_phase(domain_id, ok ? "success" : "failed");
      if (ok) setTimeout(() => set_verify_phases((prev) => {
         if (prev[domain_id] !== "success") return prev;
         const next = { ...prev };
         delete next[domain_id];
         return next;
      }), PULSE_MS + 400);
   }

   const add_domain_button = (
      <Button
         onClick={() => set_show_add_domain((prev) => !prev)}
         aria-pressed={show_add_domain}
         className="gap-1.5 transition-all duration-200 hover:-translate-y-0.5
                    hover:bg-primary/85 hover:shadow-[0_0_20px_rgba(43,216,245,0.45)]"
      >
         <Plus className="size-4"/>
         Add Domain
      </Button>
   );

   return(
      <div className = "flex flex-col gap-6 max-sm:gap-4">
         <PageHero title = "DOMAINS" />
         <div className="hidden justify-end sm:flex md:hidden">
            {add_domain_button}
         </div>

         {show_add_domain && (
            <AddDomainForm
               on_cancel={() => set_show_add_domain(false)}
               existing_domains={domains.map((d) => d.domain.toLowerCase())}
               on_added={(id) => {
                  set_show_add_domain(false);
                  if (active_tab !== "all" && active_tab !== "pending") set_active_tab("all");
                  set_search("");
                  set_selected_id(id);
                  void refetch();
               }}
            />
         )}
         <div className="flex flex-col gap-6 min-[1100px]:flex-row min-[1100px]:items-start">
            <div className = "flex min-w-0 flex-col gap-4 min-[1100px]:flex-1">
               <div className="hidden items-end justify-between gap-4 border-b border-brand-panel-border md:flex">
               <div className="flex flex-wrap items-center gap-2">
                  {tab_defs.map((tab) => (
                     <button
                        key={tab.key}
                        type="button"
                        onClick = {() => set_active_tab(tab.key)}
                        className = {cn (
                           "flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors",
                           active_tab === tab.key
                              ? "border-brand-cyan text-foreground"
                              : "border-transparent text-muted-foreground hover:text-foreground"
                        )}
                     >
                        {tab.label}
                        <span
                           className={cn(
                              "flex size-5 items-center justify-center rounded-full text-xs",
                              tab.key !== "all" && (counts?.[tab.key] ?? 0) > 0
                                 ? status_accent[tab.key].count
                                 : active_tab === tab.key
                                    ? "bg-brand-cyan/15 text-brand-cyan"
                                    : "bg-muted text-muted-foreground"
                           )}
                        >
                           {counts?.[tab.key] ?? 0}
                        </span>
                     </button>
                  ))}
               </div>
               <div className="mb-2 shrink-0">{add_domain_button}</div>
               </div>
               <div className = "flex flex-wrap items-center justify-between gap-3 max-sm:flex-nowrap max-sm:gap-2">
                  <div className = "relative w-full max-w-xs max-sm:max-w-none max-sm:flex-1">
                     <Search className = "absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                     <Input
                        type = "search"
                        aria-label = "Search domains"
                        placeholder = "Search domains..."
                        value = {search}
                        onChange = {(e) => set_search(e.target.value)}
                        autoCapitalize = "off"
                        autoCorrect = "off"
                        className = "h-9 pl-9 max-sm:h-10 max-sm:text-base"
                     />
                  </div>
                  <Select value={sort_value} onValueChange = {set_sort_value}>
                     <SelectTrigger
                        aria-label = "Sort domains"
                        className = "w-auto min-w-40 max-sm:size-10 max-sm:min-w-0 max-sm:shrink-0 max-sm:justify-center max-sm:px-0 max-sm:[&>svg:last-child]:hidden"
                     >
                        <ArrowUpDown className = "hidden size-4 max-sm:block" />
                        <span className = "max-sm:sr-only"><SelectValue /></span>
                     </SelectTrigger>
                     <SelectContent align = "end">
                        {sort_options.map((opt) => (
                           <SelectItem key = {opt.value} value={opt.value}>
                              {opt.label}
                           </SelectItem>
                        ))}
                     </SelectContent>
                  </Select>
                  <Button
                     onClick={() => set_show_add_domain(true)}
                     className = "hidden h-10 shrink-0 gap-1.5 max-sm:inline-flex"
                  >
                     <Plus className = "size-4"/>
                     Add
                  </Button>
               </div>

               {error && (
                  <div className = "rounded-lg border border-brand-alert/30 bg-brand-alert/5 px-4 py-3 text-sm text-brand-alert">
                     {error}
                  </div>
               )}

               <div className = "hidden flex-col gap-2.5 max-md:flex">
                  {domains.length === 0 && (
                     <p className = "rounded-xl border border-brand-panel-border bg-brand-panel px-4 py-8 text-center text-sm text-muted-foreground">
                        {loading ? "Loading domains..." : "No domains found."}
                     </p>
                  )}
                  {domains.map((item) => (
                     <DomainCard
                        key = {item.id}
                        domain = {item}
                        selected = {selected_id === item.id}
                        on_open = {() => set_selected_id(item.id)}
                     />
                  ))}
               </div>

               <Card className = "border border-brand-panel-border bg-gradient-to-br from-brand-panel to-brand-panel-deep py-0 ring-0 max-md:hidden">
                  <div className = "flex items-center justify-between gap-3 border-b border-brand-panel-border px-4 py-3">
                     <span className = "flex items-center gap-2 text-sm font-semibold text-foreground">
                        <Globe className = "size-4 text-brand-cyan" />
                        Your domains
                        <span className = "rounded-full bg-brand-cyan/15 px-2 py-0.5 text-xs text-brand-cyan">{counts?.all ?? 0}</span>
                     </span>
                     {counts && (
                        <span className = "flex items-center gap-3 text-xs text-muted-foreground">
                           {(["verified", "pending", "failed", "expired"] as const).filter((k) => counts[k] > 0).map((k) => (
                              <span key = {k} className = "inline-flex items-center gap-1.5">
                                 <span className = {cn("size-1.5 rounded-full", status_accent[k].dot)} />
                                 {counts[k]} {status_config[k].label.toLowerCase()}
                              </span>
                           ))}
                        </span>
                     )}
                  </div>
                  <CardContent className = "overflow-x-auto px-0 py-0">
                     <table className = "w-full border-separate border-spacing-0 text-left">
                        <thead>
                           <tr className = "text-xs whitespace-nowrap [&>th]:border-b [&>th]:border-brand-panel-border text-muted-foreground uppercase tracking-wide">
                              <th className = "px-3 py-2.5 font-medium">Domain</th>
                              <th className = "px-3 py-2.5 font-medium">Status</th>
                              <th className = "px-3 py-2.5 font-medium">
                                 <span className = "inline-flex items-center gap-1">
                                    Added
                                    <ChevronDown className = "size-3"/>
                                 </span>
                              </th>
                              <th className = "px-3 py-2.5 font-medium">Checked</th>
                              <th className = "px-3 py-2.5 font-medium">Action</th>
                           </tr>
                        </thead>
                        <tbody>
                           {domains.length === 0 && (
                              <tr>
                                 <td colSpan={5} className = "px-3 py-8 text-center text-sm text-muted-foreground">
                                    {loading ? "Loading domains..." : "No domains found."}
                                 </td>
                              </tr>
                           )}
                           {domains.map((item) => {
                              const expanded = selected_id === item.id;
                              return (
                              <Fragment key = {item.id}>
                              <tr
                                 onClick={() => set_selected_id(expanded ? null : item.id)}
                                 aria-expanded = {expanded}
                                 style = {{ "--ring": RING_COLOR[item.status] } as React.CSSProperties}
                                 className = {cn(
                                    "group cursor-pointer text-sm transition-colors",
                                    !expanded && item.status === "pending" && "bg-brand-yellow/[0.03]",
                                    expanded ? "[&>td]:bg-brand-cyan/[0.05]" : "hover:bg-white/[0.03] [&>td]:border-b [&>td]:border-brand-panel-border last:[&>td]:border-b-0",
                                    selected_id && !expanded && "opacity-40 transition-opacity hover:opacity-100"
                                 )}
                              >
                                 <td className = {cn("px-3 py-2.5", expanded ? "rounded-tl-lg shadow-[inset_3px_0_0_var(--ring),inset_0_1px_0_var(--ring)]" : status_accent[item.status].edge)}>
                                    <span className = "flex max-w-[280px] items-center gap-2.5" title={item.domain}>
                                       <DomainTile status = {item.status} />
                                       <span className = "flex min-w-0 flex-col">
                                          <span className = "truncate font-medium text-foreground">{item.domain}</span>
                                          <span className = "truncate text-[11px] text-muted-foreground">{method_label(item.verification_method)}</span>
                                       </span>
                                    </span>
                                 </td>
                                 <td className = {cn("px-3 py-2.5", expanded && "shadow-[inset_0_1px_0_var(--ring)]")}>
                                    <span className = {cn("inline-flex rounded-full", phase_of(item) === "success" && "step-glow-success")}>
                                       <StatusBadge status={item.status} />
                                    </span>
                                 </td>
                                 <td className = {cn("px-3 py-2.5 whitespace-nowrap text-[#cbd5e1]", expanded && "shadow-[inset_0_1px_0_var(--ring)]")} title = {format_timestamp(item.created_at)}>
                                    {formatDateWithYear(item.created_at)}
                                 </td>
                                 <td className = {cn("px-3 py-2.5 whitespace-nowrap text-[#cbd5e1]", expanded && "shadow-[inset_0_1px_0_var(--ring)]")}>
                                    {item.last_checked_at ? (
                                       <span className="inline-flex items-center gap-1.5" title = {format_timestamp(item.last_checked_at)}>
                                          <span className = {cn("size-1.5 rounded-full", status_accent[item.status].dot)} />
                                          {formatDateWithYear(item.last_checked_at)}
                                       </span>
                                    ): (
                                       <span className = "text-muted-foreground">Never</span>
                                    )}
                                 </td>
                                 <td className = {cn("px-3 py-2.5", expanded && "rounded-tr-lg shadow-[inset_-1px_0_0_var(--ring),inset_0_1px_0_var(--ring)]")}>
                                    <div className = "flex items-center gap-2 whitespace-nowrap">
                                       {item.status === "verified" ? (
                                          <span className = "text-xs font-medium text-muted-foreground transition-colors group-hover:text-brand-cyan">
                                             {expanded ? "Hide" : "Details"}
                                          </span>
                                       ) : (
                                          <Button 
                                             size = "xs"
                                             variant = {item.status === "pending" ? "default" : "outline"}
                                             className = {cn(
                                                item.status === "pending" && "border-transparent bg-brand-yellow text-black hover:bg-brand-yellow/85",
                                                (item.status === "failed" || item.status === "expired") && 
                                                "border-brand-alert text-brand-alert hover:bg-brand-alert/10"
                                             )}
                                             disabled = {verifying_id === item.id}
                                             onClick={(e) => {
                                                e.stopPropagation();
                                                void handle_verify(item.id);
                                             }}
                                          >
                                             {verifying_id === item.id ? "Verifying...": item.status === "pending" ? "Verify" : "Retry"}
                                          </Button>
                                       )}
                                       <ChevronDown aria-hidden = "true" className = {cn("size-4 text-muted-foreground transition-transform group-hover:text-brand-cyan", expanded && "rotate-180 text-brand-cyan")} />
                                    </div>
                                 </td>
                              </tr>
                              {expanded && !is_narrow && (
                                 <tr className = "[&>td]:border-b [&>td]:border-brand-panel-border last:[&>td]:border-b-0" style = {{ "--ring": RING_COLOR[item.status] } as React.CSSProperties}>
                                    <td colSpan = {5} className = "p-0">
                                       <DomainExpansion
                                          domain = {item}
                                          phase = {phase_of(item)}
                                          verifying = {verifying_id === item.id}
                                          feedback = {verify_feedback[item.id]}
                                          on_verify = {(id) => void handle_verify(id)}
                                          on_delete = {(id) => void handle_delete(id)}
                                       />
                                    </td>
                                 </tr>
                              )}
                              </Fragment>
                              );
                           })}
                        </tbody>
                     </table>
                  </CardContent>
               </Card>

               <div className = "flex flex-wrap items-center justify-between gap-3">
                  <p className = "text-sm text-muted-foreground">
                     Showing {domains.length} of {pagination?.total ?? 0} domains
                  </p>
                  {pagination?.has_more && (
                     <Button
                        variant = "outline"
                        size="sm"
                        className = "gap-1.5"
                        onClick={handle_load_more}
                        disabled={loading}
                     >
                        {loading ? "Loading" : "Load more"}
                        <ChevronDown className = "size-3.5" />
                     </Button>
                  )}
               </div>
            </div>

            {selected_domain && is_narrow && (
               <>
                  <DetailSheetBackdrop onClose={() => set_selected_id(null)} />
                  <DomainDetailPanel
                     domain={selected_domain}
                     phase={phase_of(selected_domain)}
                     on_close={() => set_selected_id(null)}
                     on_verify={(id) => void handle_verify(id)}
                     on_delete={(id) => void handle_delete(id)}
                     verifying={verifying_id === selected_domain.id}
                     feedback={verify_feedback[selected_domain.id]}
                  />
               </>
            )}
         </div>
      </div>
   );
}