"use client";
import
{
    useEffect,
    useMemo,
    useState,
} from "react";
import { ArrowRight, Globe, Lock, Mail, Sparkles, type LucideIcon } from "lucide-react";

import type
{
    brand_candidate,
    brand_candidate_status,
    brand_risk_level,
} from "@/lib/brandIntelligenceTypes";
import { cn } from "@/lib/utils";
import BrandCandidateInvestigation from "./BrandCandidateInvestigation";
import { LookAlikeDomain, technique_label } from "./lookalike";
import { update_brand_candidate_status } from "@/lib/brandIntelligenceService";
import { PANEL, TAG } from "./brandStyles";


interface BrandCandidateListProps
{
    candidates: brand_candidate[];
    domain: string | null;
    search: string;
    risk: brand_risk_level | "all";
    status: brand_candidate_status | "all";
    onClearFilters: () => void;
}






function risk_text(risk: brand_risk_level): string
{
    return risk === "critical" ? "text-brand-alert" : risk === "high" ? "text-brand-orange" : risk === "medium" ? "text-brand-yellow" : "text-brand-success";
}


function status_label(status: brand_candidate_status): string
{
    switch (status)
    {
        case "under_review":
            return "Under review";

        case "confirmed_impersonation":
            return "Confirmed";

        case "false_positive":
            return "False positive";

        case "resolved":
            return "Resolved";

        default:
            return "New";
    }
}


const RISK_ORDER: brand_risk_level[] = ["critical", "high", "medium", "low"];

function evidence_icons(candidate: brand_candidate): { label: string; icon: LucideIcon; present: boolean; title: string }[]
{
    const signals = candidate.evidence.signals ?? {};
    return [
        {
            label: "Live", icon: Globe, present: Boolean(signals.is_resolvable),
            title: signals.is_resolvable ? `Live: resolves to ${signals.ip_addresses?.join(", ") || "an IP address"}` : "Not live",
        },
        {
            label: "Mail server", icon: Mail, present: Boolean(signals.has_mx),
            title: signals.has_mx ? `Mail server: ${signals.mx_records?.join(", ") || "set up"}` : "No mail server",
        },
        {
            label: "HTTPS", icon: Lock, present: Boolean(signals.has_tls),
            title: signals.has_tls ? `HTTPS${signals.tls_issuer ? `: certificate from ${signals.tls_issuer}` : ""}` : "No HTTPS",
        },
        {
            label: "New domain", icon: Sparkles, present: Boolean(signals.is_newly_registered),
            title: signals.is_newly_registered ? `Newly registered${signals.days_old != null ? ` (${signals.days_old} days ago)` : ""}` : "Not newly registered",
        },
    ];
}


const RISK_EDGE: Record<brand_risk_level, string> = {
    critical: "var(--color-brand-alert)",
    high: "var(--color-brand-orange)",
    medium: "var(--color-brand-yellow)",
    low: "var(--color-brand-success)",
};

const STATUS_PILL: Record<brand_candidate_status, string> = {
    new: "border-brand-cyan/60 bg-brand-cyan/10 text-brand-cyan",
    under_review: "border-[#a78bfa]/60 bg-[#a78bfa]/10 text-[#a78bfa]",
    confirmed_impersonation: "border-[#991b1b] bg-brand-alert/10 text-brand-alert",
    false_positive: "border-[#334155] bg-[#334155]/10 text-[#94a3b8]",
    resolved: "border-brand-success/60 bg-brand-success/10 text-brand-success",
};

function CandidateCard({ candidate, original, onOpen, showFound }: { candidate: brand_candidate; original: string | null; onOpen: () => void; showFound: boolean })
{
    const technique = technique_label(candidate.evidence.mutation?.mutation_type);
    const first = relative_time(candidate.first_seen);
    const seenAgain = timestamp_value(candidate.last_seen) - timestamp_value(candidate.first_seen) > 86_400_000;
    const details = [
        technique,
        showFound ? `Found ${first.toLowerCase()}` : null,
        seenAgain ? `seen again ${relative_time(candidate.last_seen).toLowerCase()}` : null,
    ].filter(Boolean).join(" · ");
    return (
        <button
            type="button"
            onClick={onOpen}
            title={`Risk score ${candidate.risk_score}/100 · open the investigation`}
            className={cn(PANEL, "group flex flex-col gap-1.5 text-left transition-colors hover:border-brand-cyan/40")}
            style={{ boxShadow: `inset 3px 0 0 ${RISK_EDGE[candidate.risk_level]}` }}
        >
            <span className="flex items-center gap-2">
                <span className="min-w-0 flex-1 truncate text-base leading-tight font-semibold text-foreground" title={candidate.candidate_domain}>
                    <LookAlikeDomain candidate={candidate.candidate_domain} original={original} />
                </span>
                <span
                    title={candidate.status === "new" ? "New, not reviewed yet" : undefined}
                    className={cn(TAG, STATUS_PILL[candidate.status])}
                >
                    {status_label(candidate.status)}
                </span>
            </span>
            <span className="truncate text-[11px] text-[#94a3b8]" title={`First seen ${format_timestamp(candidate.first_seen)} · last seen ${format_timestamp(candidate.last_seen)}`}>
                {details}
            </span>
            <span className="mt-3 flex items-center justify-between gap-2">
                <span className="flex shrink-0 items-center gap-3.5">
                    {evidence_icons(candidate).map((item) => (
                        <item.icon
                            key={item.label}
                            aria-label={item.title}
                            className={cn("size-[18px]", item.present ? "text-[#cbd5e1]" : "text-muted-foreground opacity-25")}
                        >
                            <title>{item.title}</title>
                        </item.icon>
                    ))}
                </span>
                <ArrowRight aria-hidden="true" className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-brand-cyan" />
            </span>
        </button>
    );
}

function shared_found(items: brand_candidate[]): string | null
{
    if (items.length < 2) return null;
    const first = relative_time(items[0].first_seen);
    return items.every((c) => relative_time(c.first_seen) === first) ? first.toLowerCase() : null;
}

function relative_time(value: string): string
{
    const ms = Date.now() - new Date(value).getTime();
    if (Number.isNaN(ms)) return "Unavailable";
    const days = Math.floor(ms / 86_400_000);
    if (days < 1) return "Today";
    if (days === 1) return "Yesterday";
    if (days < 30) return `${days} days ago`;
    const months = Math.floor(days / 30);
    return `${months} month${months === 1 ? "" : "s"} ago`;
}

function format_timestamp(value: string): string
{
    const date = new Date(value);
    if (Number.isNaN(date.getTime()))
        return "Unavailable";
    return date.toLocaleString(
        "en-ZA",
        {
            day: "2-digit",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
        }
    );
}


function timestamp_value(value: string): number
{
    const timestamp = new Date(value).getTime();

    if (Number.isNaN(timestamp))
        return 0;

    return timestamp;
}


export default function BrandCandidateList
({
    candidates,
    domain,
    search,
    risk,
    status,
    onClearFilters,
}: BrandCandidateListProps)
{
    const [selected_candidate_id, set_selected_candidate_id] =
        useState<string | null>(null);
    const [local_candidates, set_local_candidates] =
        useState<brand_candidate[]>(candidates);

    useEffect(() =>
    {
        set_local_candidates(candidates);

    }, [candidates]);

    const selected_candidate =
        local_candidates.find
        (
            (candidate) => candidate.id === selected_candidate_id
        ) ?? null;

    useEffect(() =>
    {
        if (!selected_candidate)
            return;

        function handle_key_down(event: KeyboardEvent)
        {
            if (event.key === "Escape")
                set_selected_candidate_id(null);
        }

        window.addEventListener("keydown", handle_key_down);

        return () =>
        {
            window.removeEventListener("keydown", handle_key_down);
        };

    }, [selected_candidate]);

    const visible_candidates = useMemo(() =>
    {
        const query = search.trim().toLowerCase();
        return local_candidates
            .filter((candidate) =>
                (!query || candidate.candidate_domain.toLowerCase().includes(query))
                && (risk === "all" || candidate.risk_level === risk)
                && (status === "all" || candidate.status === status))
            .sort((first, second) => second.risk_score - first.risk_score);
    }, [local_candidates, search, risk, status]);
    const filtered = visible_candidates.length !== local_candidates.length;


    const row_groups: { key: string; level: brand_risk_level | null; items: brand_candidate[] }[] =
        RISK_ORDER
            .map((level) => ({ key: level, level, items: visible_candidates.filter((c) => c.risk_level === level) }))
            .filter((group) => group.items.length > 0);


    async function handle_status_change
    (
        candidate_id: string,
        status: brand_candidate_status,
    ): Promise<brand_candidate>
    {
        const updated_candidate =
            await update_brand_candidate_status
            (
                candidate_id,
                status,
            );

        set_local_candidates((current_candidates) =>
            current_candidates.map((candidate) =>
                candidate.id === updated_candidate.id
                    ? updated_candidate
                    : candidate
            )
        );

        return updated_candidate;
    }


    return (
        <section className="flex flex-col gap-4">



            {filtered && (
                <p className="m-0 text-sm text-muted-foreground">
                    Showing {visible_candidates.length} of {local_candidates.length} ·{" "}
                    <button type="button" onClick={onClearFilters} className="text-brand-cyan hover:underline">Clear filters</button>
                </p>
            )}

            <div>
                {visible_candidates.length === 0 ? (
                    <div className={cn(PANEL, "p-8 text-center")}>
                        <p className="font-medium text-foreground">
                            {filtered ? "No candidates match these filters" : "No candidates found yet"}
                        </p>
                        <p className="mt-1 text-sm text-muted-foreground">
                            {filtered
                                ? <button type="button" onClick={onClearFilters} className="text-brand-cyan hover:underline">Clear filters</button>
                                : "Run monitoring to discover more possible domain impersonations."}
                        </p>
                    </div>

                ) : (
                    <div className="flex flex-col gap-6">
                        {row_groups.map((group) => (
                            <section key={group.key} className="flex flex-col gap-3">
                                {group.level && (
                                    <h3 className="m-0 flex flex-wrap items-baseline gap-x-2.5 gap-y-1 text-lg uppercase">
                                        <span className={risk_text(group.level)}>{group.level}</span>
                                        <span className="text-[13px] tracking-normal text-[#94a3b8] normal-case [font-family:var(--font-body)]">
                                            · {group.items.length} candidate{group.items.length === 1 ? "" : "s"}
                                            {shared_found(group.items) && <> · found {shared_found(group.items)}</>}
                                        </span>
                                    </h3>
                                )}
                                <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
                                    {group.items.map((candidate) => (
                                        <CandidateCard
                                            key={candidate.id}
                                            candidate={candidate}
                                            original={domain}
                                            onOpen={() => set_selected_candidate_id(candidate.id)}
                                            showFound={!shared_found(group.items)}
                                        />
                                    ))}
                                </div>
                            </section>
                        ))}
                    </div>
                )}

            </div>
            {selected_candidate && (
                <div
                    className={
                        "fixed inset-0 z-50 flex items-center " +
                        "justify-center p-4 sm:p-6"
                    }
                >

                    <button
                        type="button"
                        aria-label="Close candidate investigation"
                        className="absolute inset-0 bg-black/70 backdrop-blur-[2px]"
                        onClick={() => set_selected_candidate_id(null)}
                    />


                    <div
                        role="dialog"
                        aria-modal="true"
                        aria-label={`Investigation for ${selected_candidate.candidate_domain}`}
                        className={
                            "relative z-10 max-h-[90vh] w-full max-w-6xl " +
                            "overflow-y-auto rounded-[10px] shadow-[0_12px_32px_rgba(0,0,0,0.6)]"
                        }
                    >

                        <BrandCandidateInvestigation
                            candidate={selected_candidate}
                            onStatusChange={handle_status_change}
                            onClose={() => set_selected_candidate_id(null)}
                        />

                    </div>

                </div>
            )}
        </section>
    );
}