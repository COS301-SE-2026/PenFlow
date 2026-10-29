"use client";

import {useState} from "react";
import type { ReactNode } from "react";
import
{
    Globe2,
    Mail,
    MapPin,
    Network,
    ShieldCheck,
    Shuffle,
    X,
} from "lucide-react";
import type
{
    brand_candidate,
    brand_candidate_status,
} from "@/lib/brandIntelligenceTypes";
import { cn } from "@/lib/utils";
import { Button } from "@/shared/components/ui/button";
import { FIELD, ICON_BADGE, LABEL, PANEL, RISK_TAG, SECTION_TITLE, TAG } from "./brandStyles";


interface BrandCandidateInvestigationProps
{
    candidate: brand_candidate;
    onStatusChange:
    (
        candidate_id: string,
        status: brand_candidate_status,
    ) => Promise<brand_candidate>;
    onClose: () => void;
}


const STATUS_SELECT: Record<brand_candidate_status, string> = {
    new: "border-brand-cyan/40 text-brand-cyan",
    under_review: "border-[#a78bfa]/40 text-[#a78bfa]",
    confirmed_impersonation: "border-brand-alert/40 text-brand-alert",
    false_positive: "border-brand-panel-border text-muted-foreground",
    resolved: "border-brand-success/40 text-brand-success",
};



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


function yes_no(value?: boolean): string
{
    return value ? "Yes" : "No";
}


export default function BrandCandidateInvestigation
({
    candidate,
    onStatusChange,
    onClose,
}: BrandCandidateInvestigationProps)
{
    const mutation = candidate.evidence.mutation;
    const signals = candidate.evidence.signals;
    const reasons = candidate.evidence.reasons ?? [];

    const [status_saving, set_status_saving] = useState(false);
    const [status_error, set_status_error] =
        useState<string | null>(null);


    async function handle_status_update
    (
        status: brand_candidate_status,
    )
    {
        if (status_saving || status === candidate.status)
            return;

        set_status_saving(true);
        set_status_error(null);

        try
        {
            await onStatusChange
            (
                candidate.id,
                status,
            );
        }
        catch (error)
        {
            set_status_error
            (
                error instanceof Error
                    ? error.message
                    : "Failed to update candidate status"
            );
        }
        finally
        {
            set_status_saving(false);
        }
    }

    return (
        <section
            className={
                "overflow-hidden rounded-[10px] border " +
                "border-brand-panel-border bg-[#050914]"
            }
            aria-label={`Investigation details for ${candidate.candidate_domain}`}
        >

            <div
                className={
                    "flex items-start justify-between gap-4 " +
                    "border-b border-brand-panel-border p-5"
                }
            >

                <div>

                    <p className={LABEL}>
                        Candidate investigation
                    </p>

                    <div className="mt-2 flex flex-wrap items-center gap-3">

                        <h3 className="m-0 break-all text-[28px] text-foreground max-sm:text-lg">
                            {candidate.candidate_domain}
                        </h3>

                        <span
                            className={cn(TAG, RISK_TAG[candidate.risk_level])}
                        >
                            {candidate.risk_level}
                        </span>

                        <span className="tabular-nums">
                            <strong className="text-xl text-foreground">{candidate.risk_score}</strong>
                            <span className="text-[12px] text-muted-foreground">/100</span>
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

            <div className="border-b border-brand-panel-border p-5">

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

                    <div>

                        <p className={LABEL}>
                            Review status
                        </p>

                        <p className="m-0 mt-1 text-[11px] text-[#94a3b8]">
                            Record the analyst decision for this candidate.
                        </p>

                    </div>


                    <div className="min-w-56">

                        <select
                            value={candidate.status}
                            disabled={status_saving}
                            onChange={(event) =>
                                void handle_status_update
                                (
                                    event.target.value as brand_candidate_status
                                )
                            }
                            className={cn(
                                FIELD, "w-full px-3 font-medium disabled:cursor-not-allowed disabled:opacity-60",
                                STATUS_SELECT[candidate.status]
                            )}
                        >
                            <option value="new">
                                New
                            </option>

                            <option value="under_review">
                                Under review
                            </option>

                            <option value="confirmed_impersonation">
                                Confirmed impersonation
                            </option>

                            <option value="false_positive">
                                False positive
                            </option>

                            <option value="resolved">
                                Resolved
                            </option>
                        </select>

                    </div>

                </div>


                {status_saving && (
                    <p className="mt-3 text-sm text-brand-cyan">
                        Saving review status...
                    </p>
                )}


                {status_error && (
                    <p
                        role="alert"
                        className="mt-3 text-sm text-brand-alert"
                    >
                        {status_error}
                    </p>
                )}

            </div>

            <div className="grid gap-3.5 border-b border-brand-panel-border p-5 md:grid-cols-2 xl:grid-cols-4">

                <EvidenceSummary
                    icon={<Globe2 className="size-4" />}
                    label="Registered"
                    color="#a78bfa"
                    value={format_timestamp(signals?.creation_date)}
                />

                <EvidenceSummary
                    icon={<ShieldCheck className="size-4" />}
                    label="Domain age"
                    color="#facc15"
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
                    color="#f472b6"
                    value={signals?.geo_location ?? "Unavailable"}
                />

                <EvidenceSummary
                    icon={<Network className="size-4" />}
                    label="ISP"
                    color="#4ade80"
                    value={signals?.isp ?? "Unavailable"}
                />

            </div>


            <div className="grid gap-3.5 p-5 xl:grid-cols-2">

                <div className="flex flex-col gap-3.5">

                    <div className={PANEL}>

                        <div className="flex items-center gap-2.5">

                            <SectionIcon icon={ShieldCheck} />

                            <h3 className={SECTION_TITLE}>
                                Why PenFlow flagged this domain
                            </h3>

                        </div>


                        {reasons.length === 0 ? (
                            <p className="m-0 mt-4 text-xs text-muted-foreground">
                                No scoring reasons were returned for this candidate.
                            </p>
                        ) : (
                            <ul className="m-0 mt-4 flex list-none flex-col gap-2.5 p-0">

                                {reasons.map((reason, index) => (
                                    <li
                                        key={`${candidate.id}-reason-${index}`}
                                        className="flex gap-2.5 text-sm leading-relaxed text-[#cbd5e1]"
                                    >
                                        <span className="mt-[0.55rem] size-1.5 shrink-0 rounded-full bg-brand-cyan" />
                                        <span>{reason}</span>
                                    </li>
                                ))}

                            </ul>
                        )}

                    </div>


                    <div className={cn(PANEL, "flex-1")}>

                        <div className="flex items-center gap-2.5">

                            <SectionIcon icon={Shuffle} />

                            <h3 className={SECTION_TITLE}>
                                Domain mutation
                            </h3>

                        </div>

                        <div className="mt-4 grid gap-4 sm:grid-cols-2">

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
                            <div className="mt-4">

                                <p className={LABEL}>
                                    Mutation detail
                                </p>

                                <p className="m-0 mt-1 text-sm text-foreground">
                                    {mutation.mutation_detail}
                                </p>

                            </div>
                        )}

                    </div>

                </div>


                <div className="flex flex-col gap-3.5">

                    <div className={PANEL}>

                        <div className="flex items-center gap-2.5">

                            <SectionIcon icon={Network} />

                            <h3 className={SECTION_TITLE}>
                                Network evidence
                            </h3>

                        </div>


                        <div className="mt-4 grid gap-4 sm:grid-cols-2">

                            <EvidenceValue
                                label="DNS resolves"
                                value={yes_no(signals?.is_resolvable)}
                                flag={signals?.is_resolvable}
                            />

                            <EvidenceValue
                                label="HTTPS / TLS"
                                value={yes_no(signals?.has_tls)}
                                flag={signals?.has_tls}
                            />

                        </div>


                        <EvidenceList
                            label="IP addresses"
                            values={signals?.ip_addresses}
                        />


                        <div className="mt-4">
                            <EvidenceValue
                                label="TLS issuer"
                                value={signals?.tls_issuer ?? "Unavailable"}
                            />
                        </div>

                    </div>


                    <div className={cn(PANEL, "flex-1")}>

                        <div className="flex items-center gap-2.5">

                            <SectionIcon icon={Mail} />

                            <h3 className={SECTION_TITLE}>
                                Email evidence
                            </h3>

                        </div>


                        <div className="mt-4">

                            <EvidenceValue
                                label="MX configured"
                                value={yes_no(signals?.has_mx)}
                                flag={signals?.has_mx}
                            />

                            <EvidenceList
                                label="MX records"
                                values={signals?.mx_records}
                            />

                        </div>

                    </div>

                </div>

            </div>



        </section>
    );
}



function SectionIcon({ icon: Icon }: { icon: typeof ShieldCheck })
{
    return (
        <span className={cn(ICON_BADGE, "bg-brand-cyan/10 text-brand-cyan")}>
            <Icon className="size-4" />
        </span>
    );
}


function EvidenceValue
({
    label,
    value,
    flag,
}: {
    label: string;
    value: string;
    flag?: boolean;
})
{
    const missing = value === "Unavailable";
    return (
        <div>

            <p className={LABEL}>
                {label}
            </p>

            {flag !== undefined || value === "Yes" || value === "No" ? (
                <span
                    className={cn(
                        TAG, "mt-1.5",
                        value === "Yes" ? "border-[#991b1b] bg-brand-alert/10 text-brand-alert" : "border-[#334155] bg-[#334155]/10 text-[#94a3b8]"
                    )}
                >
                    {value}
                </span>
            ) : (
                <p className={cn("m-0 mt-1 break-words text-sm", missing ? "text-muted-foreground" : "text-foreground")}>
                    {value}
                </p>
            )}

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
        <div className="mt-4">

            <p className={LABEL}>
                {label}
            </p>

            {!values || values.length === 0 ? (
                <p className="m-0 mt-1 text-sm text-muted-foreground">
                    None observed
                </p>
            ) : (
                <div className="mt-2 flex flex-wrap gap-2">

                    {values.map((value) => (
                        <span
                            key={value}
                            className="rounded-[4px] border border-[#26364e] px-1.5 py-0.5 font-mono text-[11px] text-[#9eacbd]"
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
    color,
}: {
    icon: ReactNode;
    label: string;
    value: string;
    color: string;
})
{
    return (
        <div className={cn(PANEL, "flex items-center gap-3")}>

            <span
                className={ICON_BADGE}
                style={{ color, backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)` }}
            >
                {icon}
            </span>

            <div className="min-w-0">
                <p className={LABEL}>
                    {label}
                </p>

                <p className={cn("m-0 mt-0.5 break-words text-sm font-medium", value === "Unavailable" ? "text-muted-foreground" : "text-foreground")}>
                    {value}
                </p>
            </div>

        </div>
    );
}