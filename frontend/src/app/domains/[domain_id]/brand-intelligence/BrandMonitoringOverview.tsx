"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import
{
    AlertTriangle,
    ArrowLeft,
    BarChart3,
    ChevronRight,
    Filter,
    Play,
    RefreshCw,
    Search,
    ShieldAlert,
    ShieldCheck,
} from "lucide-react";

import { fetch_brand_monitoring, trigger_brand_monitoring } from "@/lib/brandIntelligenceService";
import type { brand_candidate_status, brand_monitoring, brand_risk_level } from "@/lib/brandIntelligenceTypes";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/lib/utils";
import PageHero from "@/shared/components/PageHero";
import BrandCandidateList from "./BrandCandidateList";
import { FIELD, ICON_BADGE, LABEL, PANEL, SECTION_TITLE } from "./brandStyles";
import { listScanSchedules } from "@/lib/scanScheduleService";


interface BrandMonitoringOverviewProps
{
    domainId: string;
    domain: string | null;
}

const MONITORING_POLL_MS = 5000;
const MONITORING_TIMEOUT_MS = 10 * 60 * 1000;
const STALE_AFTER_DAYS = 7;
type monitoring_state =
    | { status: "loading" }
    | { status: "not_configured" }
    | { status: "ready"; monitoring: brand_monitoring }
    | { status: "error"; message: string };


function error_message(error: unknown): string
{
    if (error instanceof Error)
        return error.message;

    return "Failed to load brand monitoring. Please try again.";
}


function format_timestamp(value: string | null): string
{
    if (!value)
        return "Not scheduled";
    const date = new Date(value);
    if (Number.isNaN(date.getTime()))
        return "Unavailable";
    return date.toLocaleString(
        "en-ZA",
        {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        }
    );
}

function format_date(value: string): string
{
    const date = new Date(value);
    if (Number.isNaN(date.getTime()))
        return "Unavailable";
    return date.toLocaleDateString("en-ZA", { day: "2-digit", month: "short", year: "numeric" });
}

function relative_days(value: string): string
{
    const days = Math.floor((Date.now() - new Date(value).getTime()) / 86_400_000);
    if (Number.isNaN(days)) return "Unavailable";
    if (days < 1) return "Today";
    if (days === 1) return "Yesterday";
    return `${days} days ago`;
}

function wait(milliseconds: number): Promise<void>
{
    return new Promise((resolve) =>
    {
        setTimeout(resolve, milliseconds);
    });
}


function format_elapsed(seconds: number): string
{
    const minutes = Math.floor(seconds / 60);
    const remaining_seconds = seconds % 60;
    return `${minutes}:${remaining_seconds.toString().padStart(2, "0")}`;
}


export default function BrandMonitoringOverview
({
    domainId,
    domain,
}: BrandMonitoringOverviewProps)
{
    const [state, set_state] = useState<monitoring_state>({ status: "loading" });
    const [refresh_key, set_refresh_key] = useState(0);
    const [triggering, set_triggering] = useState(false);
    const [monitoring_running, set_monitoring_running] = useState(false);
    const [run_elapsed, set_run_elapsed] = useState(0);
    const [trigger_error, set_trigger_error] = useState<string | null>(null);
    const [trigger_notice, set_trigger_notice] = useState<string | null>(null);
    const [next_scan, set_next_scan] = useState<string | null>(null);
    const [search_query, set_search_query] = useState("");
    const [risk_filter, set_risk_filter] = useState<brand_risk_level | "all">("all");
    const [status_filter, set_status_filter] = useState<brand_candidate_status | "all">("all");

    useEffect(() =>
    {
        let cancelled = false;
        //load monitoring when the page opens or refresh is pressed
        async function load_monitoring()
        {
            set_state({ status: "loading" });
            try
            {
                const monitoring = await fetch_brand_monitoring(domainId);

                const schedules = await listScanSchedules()
                    .catch(() => []);

                const schedule = schedules.find
                (
                    (item) =>
                        item.verified_domain_id === domainId
                        && item.is_active
                );

                set_next_scan(schedule?.next_run_at ?? null);
                //dont update an old page after the user leaves
                if (cancelled)
                    return;
                if (!monitoring)
                {
                    set_state({ status: "not_configured" });
                    return;
                }

                set_state
                ({
                    status: "ready",
                    monitoring,
                });
            }
            catch (error)
            {
                if (cancelled)
                    return;

                const message = error_message(error);

                //this just means monitoring has no started yet
                if (/monitoring not configured/i.test(message))
                {
                    set_state({ status: "not_configured" });
                    return;
                }

                set_state({
                    status: "error",
                    message,
                });
            }
        }

        void load_monitoring();
        return () =>
        {
            cancelled = true;
        };

    }, [domainId, refresh_key]);

    useEffect(() =>
    {
        if (!monitoring_running)
        {
            set_run_elapsed(0);
            return;
        }

        const started_at = Date.now();

        const timer = setInterval(() =>
        {
            set_run_elapsed
            (
                Math.floor((Date.now() - started_at) / 1000)
            );
        }, 1000);

        return () =>
        {
            clearInterval(timer);
        };

    }, [monitoring_running]);


    async function handle_trigger_monitoring()
    {
        if (triggering || monitoring_running)
            return;

        //we compare against this to know when the worker has actually finished
        const previous_last_run =
            state.status === "ready"
                ? state.monitoring.last_run_at
                : null;

        set_triggering(true);
        set_trigger_error(null);
        set_trigger_notice(null);

        try
        {
            const monitoring = await trigger_brand_monitoring(domainId);

            set_state
            ({
                status: "ready",
                monitoring,
            });

            //the POST only queues the celery job, it doesnt mean the scan is done
            set_triggering(false);
            set_monitoring_running(true);

            set_trigger_notice
            (
                "Monitoring is running. Waiting for the worker to finish."
            );

            const timeout_at = Date.now() + MONITORING_TIMEOUT_MS;

            while (Date.now() < timeout_at)
            {
                await wait(MONITORING_POLL_MS);

                const updated_monitoring =
                    await fetch_brand_monitoring(domainId);

                set_state
                ({
                    status: "ready",
                    monitoring: updated_monitoring,
                });

                //last_run_at is only updated once worker results are stored
                if
                (
                    updated_monitoring.last_run_at &&
                    updated_monitoring.last_run_at !== previous_last_run
                )
                {
                    set_trigger_notice
                    (
                        "Monitoring complete. Results have been refreshed."
                    );

                    return;
                }
            }

            set_trigger_notice(null);
            set_trigger_error
            (
                "Monitoring is taking longer than expected. " +
                "Refresh the page in a moment."
            );
        }
        catch (error)
        {
            set_trigger_notice(null);
            set_trigger_error(error_message(error));
        }
        finally
        {
            set_triggering(false);
            set_monitoring_running(false);
        }
    }


    const display_domain = domain ?? domainId;
    const next_run = next_scan ?? (state.status === "ready" ? state.monitoring.next_run_at : null);
    const last_run_days = state.status === "ready" && state.monitoring.last_run_at
        ? Math.floor((Date.now() - new Date(state.monitoring.last_run_at).getTime()) / 86_400_000)
        : null;
    const monitoring_status: "active" | "paused" | "stale" =
        state.status === "ready" && !state.monitoring.is_active ? "paused"
            : !next_run && (last_run_days === null || last_run_days >= STALE_AFTER_DAYS) ? "stale"
            : "active";
    return (
        <div className="flex flex-col gap-6">
            <PageHero title="BRAND INTELLIGENCE" />
            <div className="flex flex-wrap items-center justify-between gap-2">

                <Link
                    href="/domains"
                    className="inline-flex items-center gap-1 text-sm text-brand-cyan hover:underline"
                >
                    <ArrowLeft className="size-4" />
                    Back to Domains
                </Link>


            </div>

            {trigger_error && (
                <div
                    role="alert"
                    className="rounded-lg border border-brand-alert/30 bg-brand-alert/5 px-4 py-3 text-sm text-brand-alert"
                >
                    {trigger_error}
                </div>
            )}


            {trigger_notice && (
                <div
                    role="status"
                    className={
                        "rounded-lg border border-brand-success/30 " +
                        "bg-brand-success/5 px-4 py-3 text-sm text-brand-success " +
                        (monitoring_running ? "animate-pulse" : "")
                    }
                >
                    {trigger_notice}
                </div>
            )}



            <div>
                <h2 className={SECTION_TITLE}>
                    Impersonation candidates
                </h2>
                <p className="m-0 mt-1.5 text-sm text-muted-foreground">
                    Domains discovered and scored by the Brand Intelligence engine.
                </p>
            </div>

            <section className={cn(PANEL, "max-[650px]:p-3")}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="flex min-w-0 items-center gap-3">
                        <span className={cn(ICON_BADGE, "size-10 bg-brand-cyan/10 text-brand-cyan")}>
                            <ShieldCheck className="size-5" />
                        </span>
                        <div className="min-w-0">
                            <p className={LABEL}>Verified domain</p>
                            <div className="flex flex-wrap items-center gap-2.5">
                                <h2 className="m-0 truncate text-[28px] text-foreground max-sm:text-lg">{display_domain}</h2>
                                {state.status === "ready" && <MonitoringStatusPill status={monitoring_status} />}
                            </div>
                        </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">

                        <Button
                        variant="outline"
                        disabled={state.status === "loading" || triggering || monitoring_running}
                        onClick={() => set_refresh_key((current) => current + 1)}
                    >
                        <RefreshCw className="size-4" />
                        Refresh
                    </Button>

                        <Button
                        disabled={state.status === "loading" || triggering || monitoring_running}
                        onClick={() => void handle_trigger_monitoring()}
                    >
                        {triggering || monitoring_running? (
                            <RefreshCw className="size-4 animate-spin" />
                        ) : (
                            <Play className="size-4" />
                        )}

                        {triggering
                            ? "Starting..."
                            :monitoring_running
                                ? `Running ${format_elapsed(run_elapsed)}`
                                : state.status === "not_configured"
                                    ? "Start monitoring"
                                    : "Run monitoring"}
                    </Button>

                    </div>
                </div>


                {state.status === "loading" && (
                    <p
                        role="status"
                        className="mt-6 text-sm text-muted-foreground"
                    >
                        Loading monitoring info...
                    </p>
                )}


                {state.status === "not_configured" && (
                    <div className="mt-6 rounded-[10px] border border-brand-panel-border bg-brand-panel-deep p-4">

                        <h3 className="font-medium text-foreground">
                            Monitoring not configured
                        </h3>

                        <p className="mt-2 text-sm text-muted-foreground">
                            No monitoring record exists for this domain yet.
                        </p>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Start monitoring to generate and investigate possible impersonation domains.
                        </p>

                    </div>
                )}


                {state.status === "error" && (
                    <div
                        role="alert"
                        className="mt-6 rounded-[10px] border border-brand-alert/30 bg-brand-alert/5 p-4"
                    >

                        <div className="flex items-center gap-2 text-brand-alert">

                            <AlertTriangle className="size-4" />

                            <h3 className="font-medium">
                                Could not load monitoring
                            </h3>

                        </div>

                        <p className="mt-2 text-sm text-muted-foreground">
                            {state.message}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                            Check the backend and/or try refreshing the monitoring state manually.
                        </p>

                        <Button
                            variant="outline"
                            className="mt-3"
                            onClick={() => set_refresh_key((current) => current + 1)}>
                            Try again
                        </Button>

                    </div>
                )}


                {state.status === "ready" && (
                    <div className="mt-5 flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-t border-brand-panel-border pt-4">
                    <dl className="m-0 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                        <Fact label="Monitoring since" title={format_timestamp(state.monitoring.created_at)}>
                            {format_date(state.monitoring.created_at)}
                        </Fact>
                        <Fact label="Last run" title={state.monitoring.last_run_at ? format_timestamp(state.monitoring.last_run_at) : undefined}>
                            <span className={cn(monitoring_status === "stale" && "font-semibold text-brand-yellow")}>
                                {state.monitoring.last_run_at ? relative_days(state.monitoring.last_run_at) : "Not run yet"}
                            </span>
                        </Fact>
                    </dl>

                        <div className="flex flex-wrap items-center gap-2 max-sm:w-full">
                            <div className="relative max-sm:flex-1">
                                <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                                <input
                                    type="search"
                                    aria-label="Search candidates"
                                    value={search_query}
                                    onChange={(event) => set_search_query(event.target.value)}
                                    placeholder="Search domains..."
                                    className={cn(FIELD, "w-64 pr-3 pl-9 max-sm:w-full")}
                                />
                            </div>
                            <div className="relative">
                                <Filter className={cn("pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2", status_filter === "all" ? "text-muted-foreground" : "text-brand-cyan")} />
                                <select
                                    aria-label="Filter by status"
                                    value={status_filter}
                                    onChange={(event) => set_status_filter(event.target.value as brand_candidate_status | "all")}
                                    className={cn(
                                        FIELD, "pr-3 pl-9",
                                        status_filter !== "all" && "border-brand-cyan/50 text-brand-cyan"
                                    )}
                                >
                                    <option value="all">All statuses</option>
                                    <option value="new">New</option>
                                    <option value="under_review">Under review</option>
                                    <option value="confirmed_impersonation">Confirmed</option>
                                    <option value="false_positive">False positive</option>
                                    <option value="resolved">Resolved</option>
                                </select>
                            </div>
                        </div>
                    </div>
                )}

                {state.status === "ready" && state.monitoring.candidates.length > 0 && (
                    <RiskTiles
                        candidates={state.monitoring.candidates}
                        selected={risk_filter}
                        onSelect={(level) => set_risk_filter((current) => (current === level ? "all" : level))}
                    />
                )}

            </section>


            {state.status === "ready" && (
                <>
                    <BrandCandidateList
                        candidates={state.monitoring.candidates}
                        domain={domain}
                        search={search_query}
                        risk={risk_filter}
                        status={status_filter}
                        onClearFilters={() =>
                        {
                            set_search_query("");
                            set_risk_filter("all");
                            set_status_filter("all");
                        }}
                    />
                </>
            )}

        </div>
    );
}


const RISK_TILE: Record<brand_risk_level, { label: string; badge: string }> = {
    critical: { label: "Critical", badge: "bg-brand-alert/10 text-brand-alert" },
    high: { label: "High", badge: "bg-brand-orange/10 text-brand-orange" },
    medium: { label: "Medium", badge: "bg-brand-yellow/10 text-brand-yellow" },
    low: { label: "Low", badge: "bg-brand-success/10 text-brand-success" },
};

function RiskTiles
({
    candidates,
    selected,
    onSelect,
}: {
    candidates: { risk_level: brand_risk_level }[];
    selected: brand_risk_level | "all";
    onSelect: (level: brand_risk_level | "all") => void;
})
{
    const levels = (["critical", "high", "medium", "low"] as brand_risk_level[])
        .map((level) => ({ level, count: candidates.filter((candidate) => candidate.risk_level === level).length }))
        .filter((tile) => tile.count > 0);
    const tiles = [
        { key: "all" as const, label: "Total candidates", count: candidates.length, icon: BarChart3, badge: "bg-brand-cyan/10 text-brand-cyan" },
        ...levels.map((tile) => ({ key: tile.level, label: RISK_TILE[tile.level].label, count: tile.count, icon: ShieldAlert, badge: RISK_TILE[tile.level].badge })),
    ];
    return (
        <div className="mt-4 grid gap-3 sm:grid-cols-[repeat(var(--tiles),minmax(0,1fr))] max-sm:grid-cols-2"
            style={{ "--tiles": tiles.length } as React.CSSProperties}
        >
            {tiles.map((tile) => {
                const active = selected === tile.key;
                return (
                    <button
                        key={tile.key}
                        type="button"
                        aria-pressed={active}
                        onClick={() => onSelect(tile.key)}
                        className={cn(
                            "group flex items-center gap-3 rounded-[10px] border px-3.5 py-3 text-left transition-colors",
                            active
                                ? "border-brand-cyan/40 bg-brand-cyan/[0.05]"
                                : "border-brand-panel-border bg-transparent hover:border-brand-cyan/40"
                        )}
                    >
                        <span className={cn(ICON_BADGE, tile.badge)}>
                            <tile.icon className="size-4" />
                        </span>
                        <span className="min-w-0 flex-1">
                            <span className="block truncate text-[11px] font-semibold text-[#cbd5e1] uppercase">{tile.label}</span>
                            <strong className="mt-1 block text-2xl leading-none text-foreground">{tile.count}</strong>
                        </span>
                        <ChevronRight className={cn("size-4 shrink-0 transition-colors", active ? "text-brand-cyan" : "text-muted-foreground group-hover:text-foreground")} />
                    </button>
                );
            })}
        </div>
    );
}


function MonitoringStatusPill({ status }: { status: "active" | "paused" | "stale" })
{
    const style = {
        active: { label: "Monitoring active", pill: "border-brand-success/60 bg-brand-success/10 text-brand-success" },
        paused: { label: "Monitoring paused", pill: "border-[#334155] bg-[#334155]/10 text-[#94a3b8]" },
        stale: { label: "Out of date", pill: "border-brand-yellow/60 bg-brand-yellow/10 text-brand-yellow" },
    }[status];
    return (
        <span className={cn("shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase", style.pill)}>
            {style.label}
        </span>
    );
}

function Fact({ label, title, children }: { label: string; title?: string; children: React.ReactNode })
{
    return (
        <div className="flex items-baseline gap-2" title={title}>
            <dt className="text-[11px] font-semibold text-[#94a3b8] uppercase">{label}</dt>
            <dd className="m-0 text-foreground">{children}</dd>
        </div>
    );
}