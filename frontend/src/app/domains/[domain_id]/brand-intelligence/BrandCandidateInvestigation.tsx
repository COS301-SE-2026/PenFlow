import type { ReactNode } from "react";
import
{
    Globe2,
    Mail,
    MapPin,
    Network,
    ShieldCheck,
    X,
} from "lucide-react";
import type
{
    brand_candidate,
    brand_risk_level,
} from "@/lib/brandIntelligenceTypes";
import { cn } from "@/lib/utils";
import { Button } from "@/shared/components/ui/button";


interface BrandCandidateInvestigationProps
{
    candidate: brand_candidate;
    onClose: () => void;
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


//make the mutation name easier to read
function mutation_label(value?: string): string
{
    if (!value)
        return "Unknown/Unreadable mutation";

    return value
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}


function format_timestamp(value?: string | null): string
{
    if (!value)
        return "Unavailable";
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


//small helper for yes no instances
function yes_no(value?: boolean): string
{
    return value ? "Yes" : "No";
}


export default function BrandCandidateInvestigation
({
    candidate,
    onClose,
}: BrandCandidateInvestigationProps)
{
    const mutation = candidate.evidence.mutation;
    const signals = candidate.evidence.signals;
    const reasons = candidate.evidence.reasons ?? [];


    return (
        <section
            className={
                "overflow-hidden rounded-xl border " +
                "border-brand-panel-border bg-brand-panel"
            }
            aria-label={`Investigation details for ${candidate.candidate_domain}`}
        >

            <div
                className={
                    "flex items-start justify-between gap-4 " +
                    "border-b border-brand-panel-border " +
                    "bg-brand-panel-deep/40 p-5"
                }
            >

                <div>

                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Candidate investigation
                    </p>

                    <div className="mt-2 flex flex-wrap items-center gap-3">

                        <h3 className="break-all text-xl font-semibold text-foreground">
                            {candidate.candidate_domain}
                        </h3>

                        <span
                            className={cn(
                                "inline-flex rounded-full border px-2 py-1 text-xs font-medium uppercase",
                                risk_style(candidate.risk_level)
                            )}
                        >
                            {candidate.risk_level}
                        </span>

                        <span className="font-mono text-sm text-foreground">
                            {candidate.risk_score}/100
                        </span>

                    </div>

                </div>


                <Button
                    variant="outline"
                    size="icon"
                    className={
                        "shrink-0 border-brand-panel-border " +
                        "hover:border-brand-cyan/60 hover:text-brand-cyan"
                    }
                    aria-label="Close candidate investigation"
                    onClick={onClose}
                >
                    <X className="size-4" />
                </Button>

            </div>


            <div className="grid gap-5 p-5 xl:grid-cols-2">

                <div className="flex flex-col gap-5">

                    <div className="rounded-lg border border-brand-panel-border bg-brand-panel-deep p-4">

                        <div className="flex items-center gap-2">

                            <ShieldCheck className="size-4 text-brand-cyan" />

                            <h4 className="font-medium text-foreground">
                                Why PenFlow flagged this domain
                            </h4>

                        </div>


                        {reasons.length === 0 ? (
                            <p className="mt-3 text-sm text-muted-foreground">
                                No scoring reasons were returned for this candidate.
                            </p>
                        ) : (
                            <ul className="mt-3 flex flex-col gap-2">

                                {reasons.map((reason, index) => (
                                    <li
                                        key={`${candidate.id}-reason-${index}`}
                                        className="flex gap-2 text-sm text-muted-foreground"
                                    >
                                        <span className="mt-2 size-1.5 shrink-0 rounded-full bg-brand-cyan" />
                                        <span>{reason}</span>
                                    </li>
                                ))}

                            </ul>
                        )}

                    </div>


                    <div className="rounded-lg border border-brand-panel-border bg-brand-panel-deep p-4">

                        <h4 className="font-medium text-foreground">
                            Domain mutation
                        </h4>

                        <div className="mt-3 grid gap-3 sm:grid-cols-2">

                            <EvidenceValue
                                label="Mutation type"
                                value={mutation_label(mutation?.mutation_type)}
                            />

                            <EvidenceValue
                                label="Normalised domain"
                                value={
                                    mutation?.normalized_domain ??
                                    candidate.normalized_domain
                                }
                            />

                        </div>


                        {mutation?.mutation_detail && (
                            <div className="mt-3">

                                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                                    Mutation detail
                                </p>

                                <p className="mt-1 text-sm text-foreground">
                                    {mutation.mutation_detail}
                                </p>

                            </div>
                        )}

                    </div>

                </div>


                <div className="flex flex-col gap-5">

                    <div className="rounded-lg border border-brand-panel-border bg-brand-panel-deep p-4">

                        <div className="flex items-center gap-2">

                            <Network className="size-4 text-brand-cyan" />

                            <h4 className="font-medium text-foreground">
                                Network evidence
                            </h4>

                        </div>


                        <div className="mt-3 grid gap-3 sm:grid-cols-2">

                            <EvidenceValue
                                label="DNS resolves"
                                value={yes_no(signals?.is_resolvable)}
                            />

                            <EvidenceValue
                                label="HTTPS / TLS"
                                value={yes_no(signals?.has_tls)}
                            />

                        </div>


                        <EvidenceList
                            label="IP addresses"
                            values={signals?.ip_addresses}
                        />


                        <EvidenceValue
                            label="TLS issuer"
                            value={signals?.tls_issuer ?? "Unavailable"}
                        />

                    </div>


                    <div className="rounded-lg border border-brand-panel-border bg-brand-panel-deep p-4">

                        <div className="flex items-center gap-2">

                            <Mail className="size-4 text-brand-cyan" />

                            <h4 className="font-medium text-foreground">
                                Email evidence
                            </h4>

                        </div>


                        <div className="mt-3">

                            <EvidenceValue
                                label="MX configured"
                                value={yes_no(signals?.has_mx)}
                            />

                            <EvidenceList
                                label="MX records"
                                values={signals?.mx_records}
                            />

                        </div>

                    </div>

                </div>

            </div>


            <div className="grid gap-4 border-t border-brand-panel-border p-5 md:grid-cols-2 xl:grid-cols-4">

                <EvidenceSummary
                    icon={<Globe2 className="size-4" />}
                    label="Registered"
                    value={format_timestamp(signals?.creation_date)}
                />

                <EvidenceSummary
                    icon={<ShieldCheck className="size-4" />}
                    label="Domain age"
                    value={
                        signals?.days_old !== null &&
                        signals?.days_old !== undefined
                            ? `${signals.days_old} days`
                            : "Unavailable"
                    }
                />

                <EvidenceSummary
                    icon={<MapPin className="size-4" />}
                    label="Location"
                    value={signals?.geo_location ?? "Unavailable"}
                />

                <EvidenceSummary
                    icon={<Network className="size-4" />}
                    label="ISP"
                    value={signals?.isp ?? "Unavailable"}
                />

            </div>

        </section>
    );
}


function EvidenceValue
({
    label,
    value,
}: {
    label: string;
    value: string;
})
{
    return (
        <div>

            <p className="text-xs uppercase tracking-wide text-muted-foreground">
                {label}
            </p>

            <p className="mt-1 break-words text-sm text-foreground">
                {value}
            </p>

        </div>
    );
}


function EvidenceList
({
    label,
    values,
}: {
    label: string;
    values?: string[];
})
{
    return (
        <div className="mt-3">

            <p className="text-xs uppercase tracking-wide text-muted-foreground">
                {label}
            </p>

            {!values || values.length === 0 ? (
                <p className="mt-1 text-sm text-muted-foreground">
                    None observed
                </p>
            ) : (
                <div className="mt-2 flex flex-wrap gap-2">

                    {values.map((value) => (
                        <span
                            key={value}
                            className="rounded-md border border-brand-panel-border px-2 py-1 font-mono text-xs text-foreground"
                        >
                            {value}
                        </span>
                    ))}

                </div>
            )}

        </div>
    );
}


function EvidenceSummary
({
    icon,
    label,
    value,
}: {
    icon: ReactNode;
    label: string;
    value: string;
})
{
    return (
        <div className="rounded-lg border border-brand-panel-border bg-brand-panel-deep p-3">

            <div className="flex items-center gap-2 text-brand-cyan">
                {icon}

                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    {label}
                </p>
            </div>

            <p className="mt-2 break-words text-sm text-foreground">
                {value}
            </p>

        </div>
    );
}