"use client";
import type { ReactNode } from "react";
import
{
    useEffect,
    useMemo,
    useState,
} from "react";
import { RotateCcw, ScanSearch, Search} from "lucide-react";

import type
{
    brand_candidate,
    brand_candidate_status,
    brand_risk_level,
} from "@/lib/brandIntelligenceTypes";
import { cn } from "@/lib/utils";
import { Button } from "@/shared/components/ui/button";
import BrandCandidateInvestigation from "./BrandCandidateInvestigation";
import { update_brand_candidate_status } from "@/lib/brandIntelligenceService";


interface BrandCandidateListProps
{
    candidates: brand_candidate[];
}
//filters
type risk_filter =
    | "all"
    | brand_risk_level;

type status_filter =
    | "all"
    | brand_candidate_status;

type candidate_sort =
    | "risk_high"
    | "risk_low"
    | "newest"
    | "oldest"
    | "recent";


//keep the risk colours in one place
function risk_style(risk: brand_risk_level): string
{
    switch (risk)
    {
        case "critical":
            return "border-brand-alert/40 bg-brand-alert/10 text-brand-alert";

        case "high":
            return "border-brand-orange/40 bg-brand-orange/10 text-brand-orange";

        case "medium":
            return "border-brand-yellow/40 bg-brand-yellow/10 text-brand-yellow";

        default:
            return "border-brand-success/40 bg-brand-success/10 text-brand-success";
    }
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


//turn stored timestamps into numbers so candidates can be sorted
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
}: BrandCandidateListProps)
{
    const [selected_candidate_id, set_selected_candidate_id] =
        useState<string | null>(null);
    const [local_candidates, set_local_candidates] =
        useState<brand_candidate[]>(candidates);
    const [search_query, set_search_query] = useState("");
    const [selected_risk, set_selected_risk] = useState<risk_filter>("all");
    const [selected_status, set_selected_status] = useState<status_filter>("all");
    const [selected_sort, set_selected_sort] = useState<candidate_sort>("risk_high");

    //sync candidates after a new monitoring run updates the parent
    useEffect(() =>
    {
        set_local_candidates(candidates);

    }, [candidates]);

    const selected_candidate =
        local_candidates.find
        (
            (candidate) => candidate.id === selected_candidate_id
        ) ?? null;

    //allow the investigation popup to close with escape
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

    //filter and sort without changing backen
    const visible_candidates = useMemo(() =>
    {
        const query = search_query.trim().toLowerCase();
        const filtered = local_candidates.filter((candidate) =>
        {
            const matches_search =
                !query ||
                candidate.candidate_domain
                    .toLowerCase()
                    .includes(query);

            const matches_risk =
                selected_risk === "all" ||
                candidate.risk_level === selected_risk;

            const matches_status =
                selected_status === "all" ||
                candidate.status === selected_status;

            return (
                matches_search &&
                matches_risk &&
                matches_status
            );
        });


        return [...filtered].sort((first, second) =>
        {
            switch (selected_sort)
            {
                case "risk_low":
                    return first.risk_score - second.risk_score;

                case "newest":
                    return (
                        timestamp_value(second.first_seen) -
                        timestamp_value(first.first_seen)
                    );

                case "oldest":
                    return (
                        timestamp_value(first.first_seen) -
                        timestamp_value(second.first_seen)
                    );

                case "recent":
                    return (
                        timestamp_value(second.last_seen) -
                        timestamp_value(first.last_seen)
                    );

                default:
                    return second.risk_score - first.risk_score;
            }
        });

    }, [
        local_candidates,
        search_query,
        selected_risk,
        selected_sort,
        selected_status,
    ]);


    function reset_filters()
    {
        set_search_query("");
        set_selected_risk("all");
        set_selected_status("all");
        set_selected_sort("risk_high");
    }

    //save the new review status and replace the updated candidate
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

    //summary numbers for the monitoring overview
    const high_risk = local_candidates.filter
    (
        (candidate) => candidate.risk_level === "high" ||
            candidate.risk_level === "critical"
    ).length;

    const new_candidates = local_candidates.filter
    (
        (candidate) => candidate.status === "new"
    ).length;

    const under_review = local_candidates.filter
    (
        (candidate) => candidate.status === "under_review"
    ).length;


    return (
        <section className="flex flex-col gap-4">

            <div>
                <h2 className="text-lg font-semibold text-foreground">
                    Impersonation candidates
                </h2>
                <p className="text-sm text-muted-foreground">
                    Domains discovered and scored by the Brand Intelligence engine.
                </p>
            </div>


            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">

                <SummaryCard
                    label="Detected"
                    value={local_candidates.length}
                />

                <SummaryCard
                    label="High risk"
                    value={high_risk}
                />

                <SummaryCard
                    label="New"
                    value={new_candidates}
                />

                <SummaryCard
                    label="Under review"
                    value={under_review}
                />

            </div>

            <div className="rounded-lg border border-brand-panel-border bg-brand-panel p-4">
               <div className="flex flex-col gap-4 xl:flex-row xl:items-end">
                    <div className="flex-1">
                        <label
                            htmlFor="brand-candidate-search"
                            className="text-xs uppercase tracking-wide text-muted-foreground"
                        >
                            Search candidates
                        </label>
                        <div className="relative mt-2">
                            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"/>

                            <input
                                id="brand-candidate-search"
                                type="search"
                                value={search_query}
                                placeholder="Search domain..."
                                onChange={(event) =>
                                    set_search_query(event.target.value)
                                }
                                className={
                                    "h-10 w-full rounded-md border " +
                                    "border-brand-panel-border bg-brand-panel-deep " +
                                    "pl-9 pr-3 text-sm text-foreground outline-none " +
                                    "placeholder:text-muted-foreground " +
                                    "focus:border-brand-cyan"
                                }
                            />

                        </div>

                    </div>


                    <FilterSelect
                        label="Risk"
                        value={selected_risk}
                        onChange={(value) =>
                            set_selected_risk(value as risk_filter)
                        }
                    >
                        <option value="all">All risks</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </FilterSelect>


                    <FilterSelect
                        label="Status"
                        value={selected_status}
                        onChange={(value) =>
                            set_selected_status(value as status_filter)
                        }
                    >
                        <option value="all">All statuses</option>
                        <option value="new">New</option>
                        <option value="under_review">Under review</option>
                        <option value="confirmed_impersonation">
                            Confirmed
                        </option>
                        <option value="false_positive">
                            False positive
                        </option>
                        <option value="resolved">
                            Resolved
                        </option>
                    </FilterSelect>


                    <FilterSelect
                        label="Sort by"
                        value={selected_sort}
                        onChange={(value) =>
                            set_selected_sort(value as candidate_sort)
                        }
                    >
                        <option value="risk_high">
                            Highest risk
                        </option>
                        <option value="risk_low">
                            Lowest risk
                        </option>
                        <option value="newest">
                            Newest first
                        </option>
                        <option value="oldest">
                            Oldest first
                        </option>
                        <option value="recent">
                            Recently seen
                        </option>
                    </FilterSelect>


                    <Button
                        variant="outline"
                        className="h-10 shrink-0"
                        onClick={reset_filters}
                    >
                        <RotateCcw className="size-4" />
                        Reset
                    </Button>

                </div>


                <p className="mt-3 text-xs text-muted-foreground">
                    Showing {visible_candidates.length} of {local_candidates.length} candidates
                </p>

            </div>

            <div className="overflow-hidden rounded-lg border border-brand-panel-border bg-brand-panel">
                {local_candidates.length === 0 ? (
                    <div className="p-8 text-center">
                        <p className="font-medium text-foreground">
                            No candidates match the filters in place
                        </p>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Run monitoring to discover more possible domain impersonations.
                        </p>
                    </div>

                ) : visible_candidates.length === 0 ? (

                    <div className="p-8 text-center">
                        <p className="font-medium text-foreground">
                            No candidates match these filters
                        </p>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Change the search or filter options to show more candidates.
                        </p>

                        <Button
                            variant="outline"
                            className="mt-4"
                            onClick={reset_filters}
                        >
                            <RotateCcw className="size-4" />
                            Clear filters
                        </Button>

                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full border-collapse text-left">
                            <thead>
                                <tr className="border-b border-brand-panel-border text-xs uppercase tracking-wide text-muted-foreground">
                                    <th className="px-4 py-3 font-medium text-center">
                                        Candidate
                                    </th>
                                    <th className="px-4 py-3 font-medium text-center">
                                        Risk
                                    </th>
                                    <th className="px-4 py-3 font-medium text-center">
                                        Score
                                    </th>
                                    <th className="px-4 py-3 font-medium text-center">
                                        Status
                                    </th>
                                    <th className="px-4 py-3 font-medium text-center">
                                        First seen
                                    </th>
                                    <th className="px-4 py-3 font-medium text-center">
                                        Last seen
                                    </th>
                                    <th className="px-4 py-3 font-medium text-center">
                                        Investigation
                                    </th>
                                </tr>
                            </thead>


                            <tbody>

                                {visible_candidates.map((candidate) =>
                                {
                                    const first_reason =
                                        candidate.evidence.reasons?.[0];

                                    return (
                                        <tr
                                            key={candidate.id}
                                            className="border-b border-brand-panel-border text-sm last:border-b-0"
                                        >

                                            <td className="px-4 py-3">

                                                <p className="font-medium text-foreground">
                                                    {candidate.candidate_domain}
                                                </p>

                                                {first_reason && (
                                                    <p
                                                        className="mt-1 max-w-md truncate text-xs text-muted-foreground"
                                                        title={first_reason}
                                                    >
                                                        {first_reason}
                                                    </p>
                                                )}

                                            </td>


                                            <td className="px-4 py-3 text-center">

                                                <span
                                                    className={cn(
                                                        "inline-flex rounded-full border px-2 py-1 text-xs font-medium uppercase",
                                                        risk_style(candidate.risk_level)
                                                    )}
                                                >
                                                    {candidate.risk_level}
                                                </span>

                                            </td>


                                            <td className="px-4 py-3 font-mono text-foreground text-center">
                                                {candidate.risk_score}/100
                                            </td>


                                            <td className="px-4 py-3 text-muted-foreground text-center">
                                                {status_label(candidate.status)}
                                            </td>


                                            <td className="px-4 py-3 whitespace-nowrap text-muted-foreground text-center">
                                                {format_timestamp(candidate.first_seen)}
                                            </td>


                                            <td className="px-4 py-3 whitespace-nowrap text-muted-foreground text-center">
                                                {format_timestamp(candidate.last_seen)}
                                            </td>


                                            <td className="px-4 py-3 text-center">

                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    className={
                                                        "border-brand-cyan/50 bg-brand-cyan/10 " +
                                                        "text-brand-cyan transition-all duration-200 " +
                                                        "hover:border-brand-cyan hover:bg-brand-cyan " +
                                                        "hover:text-white hover:shadow-md"
                                                    }
                                                    onClick={() =>
                                                        set_selected_candidate_id(candidate.id)
                                                    }
                                                >
                                                    <ScanSearch className="size-4" />
                                                    Investigate
                                                </Button>

                                            </td>

                                        </tr>
                                    );
                                })}

                            </tbody>

                        </table>

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

                    {/*dull the page so th focus stays on investigation*/}
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
                            "overflow-y-auto rounded-xl shadow-2xl"
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


function SummaryCard
({
    label,
    value,
}: {
    label: string;
    value: number;
})
{
    return (
        <div className="rounded-lg border border-brand-panel-border bg-brand-panel p-4">

            <p className="text-xs uppercase tracking-wide text-muted-foreground">
                {label}
            </p>

            <p className="mt-1 text-2xl font-semibold text-foreground">
                {value}
            </p>

        </div>
    );
}


function FilterSelect
({
    label,
    value,
    onChange,
    children,
}: {
    label: string;
    value: string;
    onChange: (value: string) => void;
    children: ReactNode;
})
{
    return (
        <div className="min-w-40">

            <label className="text-xs uppercase tracking-wide text-muted-foreground">
                {label}
            </label>

            <select
                value={value}
                onChange={(event) =>
                    onChange(event.target.value)
                }
                className={
                    "mt-2 h-10 w-full rounded-md border " +
                    "border-brand-panel-border bg-brand-panel-deep " +
                    "px-3 text-sm text-foreground outline-none " +
                    "focus:border-brand-cyan"
                }
            >
                {children}
            </select>

        </div>
    );
}