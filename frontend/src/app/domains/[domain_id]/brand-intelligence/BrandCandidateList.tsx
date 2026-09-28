import type
{
    brand_candidate,
    brand_candidate_status,
    brand_risk_level,
} from "@/lib/brandIntelligenceTypes";
import { cn } from "@/lib/utils";


interface BrandCandidateListProps
{
    candidates: brand_candidate[];
}


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


export default function BrandCandidateList
({
    candidates,
}: BrandCandidateListProps)
{
    //summary numbers for the monitoring overview
    const high_risk = candidates.filter
    (
        (candidate) => candidate.risk_level === "high" ||
            candidate.risk_level === "critical"
    ).length;

    const new_candidates = candidates.filter
    (
        (candidate) => candidate.status === "new"
    ).length;

    const under_review = candidates.filter
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
                    value={candidates.length}
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


            <div className="overflow-hidden rounded-lg border border-brand-panel-border bg-brand-panel">

                {candidates.length === 0 ? (
                    <div className="p-8 text-center">

                        <p className="font-medium text-foreground">
                            No impersonation candidates found
                        </p>

                        <p className="mt-1 text-sm text-muted-foreground">
                            Candidates discovered by the next monitoring run
                            will appear here.
                        </p>

                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full border-collapse text-left">
                            <thead>
                                <tr className="border-b border-brand-panel-border text-xs uppercase tracking-wide text-muted-foreground">
                                    <th className="px-4 py-3 font-medium">
                                        Candidate
                                    </th>
                                    <th className="px-4 py-3 font-medium">
                                        Risk
                                    </th>
                                    <th className="px-4 py-3 font-medium">
                                        Score
                                    </th>
                                    <th className="px-4 py-3 font-medium">
                                        Status
                                    </th>
                                    <th className="px-4 py-3 font-medium">
                                        First seen
                                    </th>
                                    <th className="px-4 py-3 font-medium">
                                        Last seen
                                    </th>
                                </tr>
                            </thead>


                            <tbody>

                                {candidates.map((candidate) =>
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


                                            <td className="px-4 py-3">

                                                <span
                                                    className={cn(
                                                        "inline-flex rounded-full border px-2 py-1 text-xs font-medium uppercase",
                                                        risk_style(candidate.risk_level)
                                                    )}
                                                >
                                                    {candidate.risk_level}
                                                </span>

                                            </td>


                                            <td className="px-4 py-3 font-mono text-foreground">
                                                {candidate.risk_score}/100
                                            </td>


                                            <td className="px-4 py-3 text-muted-foreground">
                                                {status_label(candidate.status)}
                                            </td>


                                            <td className="px-4 py-3 whitespace-nowrap text-muted-foreground">
                                                {format_timestamp(candidate.first_seen)}
                                            </td>


                                            <td className="px-4 py-3 whitespace-nowrap text-muted-foreground">
                                                {format_timestamp(candidate.last_seen)}
                                            </td>

                                        </tr>
                                    );
                                })}

                            </tbody>

                        </table>

                    </div>
                )}

            </div>

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