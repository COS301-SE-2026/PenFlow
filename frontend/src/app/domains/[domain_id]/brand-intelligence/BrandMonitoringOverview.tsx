"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import
{
    AlertTriangle,
    ArrowLeft,
    History,
    Play,
    RefreshCw,
    ShieldCheck,
} from "lucide-react";

import { fetch_brand_monitoring, trigger_brand_monitoring } from "@/lib/brandIntelligenceService";
import type { brand_monitoring } from "@/lib/brandIntelligenceTypes";
import { Button } from "@/shared/components/ui/button";
import PageHero from "@/shared/components/PageHero";
import BrandCandidateList from "./BrandCandidateList";


interface BrandMonitoringOverviewProps
{
    domainId: string;
    domain: string | null;
}

//timing to poll
const MONITORING_POLL_MS = 5000;
const MONITORING_TIMEOUT_MS = 10 * 60 * 1000;
//monitored states
type monitoring_state =
    | { status: "loading" }
    | { status: "not_configured" }
    | { status: "ready"; monitoring: brand_monitoring }
    | { status: "error"; message: string };


//debugging
function error_message(error: unknown): string
{
    if (error instanceof Error)
        return error.message;

    return "Failed to load brand monitoring. Please try again.";
}


//formatted dates
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

//wait between checks so we dont spam the backend while the worker is busy
function wait(milliseconds: number): Promise<void>
{
    return new Promise((resolve) =>
    {
        setTimeout(resolve, milliseconds);
    });
}


//timer to show progress
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
                <div className="flex items-center gap-2">

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


            <section className="rounded-lg border border-brand-panel-border bg-brand-panel p-6">
                <div className="flex items-start gap-2">
                    <ShieldCheck className="mt-1 size-6 shrink-0 text-brand-cyan" />
                    <div className="min-w-0">
                        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            Verified domain
                        </p>
                        <h2 className="break-all text-xl font-semibold text-foreground">
                            {display_domain}
                        </h2>
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
                    <div className="mt-6 rounded-lg border border-brand-panel-border bg-brand-panel-deep p-4">

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
                        className="mt-6 rounded-lg border border-brand-alert/30 bg-brand-alert/5 p-4"
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
                    <div className="mt-6 flex flex-col gap-5">
                        <div className="flex flex-wrap items-center gap-3">
                            <span className="rounded-full border border-brand-panel-border px-3 py-1 text-xs text-foreground">
                                {state.monitoring.is_active
                                    ? "Monitoring active"
                                    : "Monitoring paused"}
                            </span>

                            <span className="text-sm text-muted-foreground">
                                {
                                    state.monitoring.candidates.filter
                                    (
                                        (candidate) =>
                                            candidate.risk_level === "high" ||
                                            candidate.risk_level === "critical"
                                    ).length
                                } high-risk candidates
                            </span>

                            <span className="text-sm text-muted-foreground">
                                {state.monitoring.candidates.length} candidates recorded
                            </span>
                        </div>

                        <div className="grid gap-4 sm:grid-cols-2">
                            <div className="rounded-lg border border-brand-panel-border bg-brand-panel-deep p-4">
                                <p className="text-xs text-muted-foreground">
                                    Last completed run
                                </p>
                                <p className="mt-1 font-medium text-foreground">
                                    {state.monitoring.last_run_at
                                        ? format_timestamp(state.monitoring.last_run_at)
                                        : "Not run yet"}
                                </p>
                            </div>

                            <div className="rounded-lg border border-brand-panel-border bg-brand-panel-deep p-4">
                                <p className="text-xs text-muted-foreground">
                                    Next scheduled run
                                </p>
                                <p className="mt-1 font-medium text-foreground">
                                    {format_timestamp(state.monitoring.next_run_at)}
                                </p>
                            </div>
                        </div>
                    </div>
                )}

            </section>


            {/*candidate list stays separate so we can idealy add filtering and investigation later on*/}
            {state.status === "ready" && (
                <>
                    <MonitoringHistory
                        monitoring={state.monitoring}
                    />
                    <BrandCandidateList
                        candidates={state.monitoring.candidates}
                    />
                </>
            )}

        </div>
    );
}


//vague history of the domain for know
function MonitoringHistory
({
    monitoring,
}: {
    monitoring: brand_monitoring;
})
{
    return (
        <section className="rounded-lg border border-brand-panel-border bg-brand-panel p-6">
            <div className="flex items-center gap-2">
                <History className="size-5 text-brand-cyan" />
                <div>

                    <h2 className="font-semibold text-foreground">
                        Monitoring history
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        Current timeline for this verified domain.
                    </p>

                </div>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-3">

                <HistoryItem
                    label="Monitoring created"
                    value={format_timestamp(monitoring.created_at)}
                />

                <HistoryItem
                    label="Last completed run"
                    value={
                        monitoring.last_run_at
                            ? format_timestamp(monitoring.last_run_at)
                            : "Not run yet"
                    }
                />

                <HistoryItem
                    label="Next scheduled run"
                    value={format_timestamp(monitoring.next_run_at)}
                />

            </div>

        </section>
    );
}


function HistoryItem
({
    label,
    value,
}: {
    label: string;
    value: string;
})
{
    return (
        <div className="rounded-lg border border-brand-panel-border bg-brand-panel-deep p-4">

            <p className="text-xs uppercase tracking-wide text-muted-foreground">
                {label}
            </p>

            <p className="mt-2 text-sm font-medium text-foreground">
                {value}
            </p>

        </div>
    );
}