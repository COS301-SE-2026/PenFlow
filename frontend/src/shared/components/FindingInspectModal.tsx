"use client"

import { useState } from "react";
import { Download, FileText, RotateCcw, X } from "lucide-react";
import SidePanelShell from "@/shared/components/SidePanelShell";
import { downloadBlob, formatDate, formatLabel } from "@/lib/serviceDeliveryUi";
import type { FindingDetail } from "@/lib/serviceDeliveryTypes";
import { evidenceStatusLabel, type EvidenceQuarantineStatus } from "@/lib/evidenceQuarantine";
import { cn } from "@/lib/utils";
import {
    downloadEvidence,
    retryEvidenceSecurityCheck,
} from "@/lib/serviceDeliveryService";

const SEVERITY_PILL: Record<string, string> = {
    critical: "border-[#ef4444]/60 bg-[#ef4444]/10 text-[#f87171]",
    high: "border-[#f97316]/60 bg-[#f97316]/10 text-[#fb923c]",
    medium: "border-[#facc15]/60 bg-[#facc15]/10 text-[#facc15]",
    low: "border-[#3b82f6]/60 bg-[#3b82f6]/10 text-[#60a5fa]",
    info: "border-[#64748b]/60 bg-[#64748b]/10 text-[#94a3b8]",
};
const SEVERITY_STRIPE: Record<string, string> = {
    critical: "border-l-[#ef4444]",
    high: "border-l-[#f97316]",
    medium: "border-l-[#facc15]",
    low: "border-l-[#3b82f6]",
    info: "border-l-[#64748b]",
};
const EVIDENCE_PILL: Record<EvidenceQuarantineStatus, string> = {
    pending: "border-brand-cyan/40 bg-brand-cyan/10 text-brand-cyan",
    clean: "border-brand-success/40 bg-brand-success/10 text-brand-success",
    rejected: "border-brand-alert/40 bg-brand-alert/10 text-brand-alert",
    failed: "border-brand-orange/40 bg-brand-orange/10 text-brand-orange",
};

const TAG = "rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-0.5 text-[10px] text-[#9eacbd]";
const SECTION_LABEL = "m-0 mb-1 text-[10px] font-semibold tracking-wide text-[#94a3b8] uppercase";

export default function FindingInspectModal({ finding, onClose }: { finding: FindingDetail; onClose: () => void }) {
    const [files, setFiles] = useState(finding.evidence_files ?? []);
    const [notice, setNotice] = useState("");
    const [retrying, setRetrying] = useState<string | null>(null);

    async function handleDownload(evidenceId: string, fileName: string) {
        setNotice("");
        try {
            const blob = await downloadEvidence(evidenceId, fileName);
            downloadBlob(fileName, blob);
        } catch (error) {
            setNotice(error instanceof Error ? error.message : "Unable to download evidence.");
        }
    }

    async function handleRetry(evidenceId: string) {
        setRetrying(evidenceId);
        setNotice("");
        try {
            const updated = await retryEvidenceSecurityCheck(evidenceId);
            setFiles((current) => current.map((file) => (file.id === updated.id ? updated : file)));
        } catch (error) {
            setNotice(error instanceof Error ? error.message : "Unable to retry the security check.");
        } finally {
            setRetrying(null);
        }
    }

    const facts: { label: string; value: string }[] = [
        { label: "Asset", value: finding.asset_identifier ?? "Not linked to an asset" },
        { label: "Status", value: formatLabel(finding.status) },
        { label: "Verified", value: finding.is_verified ? "Yes" : "No" },
        { label: "Found", value: formatDate(finding.created_at) },
    ];

    return (
        <SidePanelShell labelledBy="sd-finding-title" onClose={onClose}>
            <header className="flex items-start justify-between gap-3 border-b border-brand-panel-border p-4">
                <div className="min-w-0">
                    <h2 id="sd-finding-title" className="m-0 text-base leading-snug font-semibold tracking-normal! text-foreground [font-family:inherit]!">
                        {finding.title}
                    </h2>
                    {finding.asset_identifier && <p className="m-0 mt-0.5 text-[11px] break-all text-[#94a3b8]">{finding.asset_identifier}</p>}
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        <span className={cn("rounded-[5px] border px-2 py-0.5 text-[10px] font-bold uppercase", SEVERITY_PILL[finding.severity])}>
                            {formatLabel(finding.severity)}
                        </span>
                        {finding.cvss_score != null && <span className={TAG}>CVSS {finding.cvss_score}</span>}
                        {finding.cve_id && <span className={TAG}>{finding.cve_id}</span>}
                    </div>
                </div>
                <button
                    type="button"
                    onClick={onClose}
                    aria-label="Close finding"
                    className="grid size-8 shrink-0 place-items-center rounded-lg text-[#94a3b8] hover:bg-white/5 hover:text-foreground"
                >
                    <X className="size-4" />
                </button>
            </header>

            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-4">
                <article className={cn("rounded-lg border border-l-[3px] border-[#22324d] bg-[#0f1c30] p-4", SEVERITY_STRIPE[finding.severity])}>
                    <section>
                        <h4 className={SECTION_LABEL}>Description</h4>
                        <p className="m-0 text-sm leading-relaxed text-[#cbd5e1]">{finding.description ?? "No description provided."}</p>
                    </section>
                    <section className="mt-4">
                        <h4 className={SECTION_LABEL}>How to fix</h4>
                        <p className="m-0 text-sm leading-relaxed text-[#cbd5e1]">{finding.recommendation ?? "Recommendation not yet documented."}</p>
                    </section>
                </article>

                <dl className="m-0 mt-4 grid gap-2.5">
                    {facts.map((fact) => (
                        <div key={fact.label} className="grid grid-cols-[5.5rem_minmax(0,1fr)] items-baseline gap-3">
                            <dt className="text-[11px] tracking-wide text-[#94a3b8] uppercase">{fact.label}</dt>
                            <dd className="m-0 truncate text-sm text-foreground" title={fact.value}>{fact.value}</dd>
                        </div>
                    ))}
                </dl>

                <section className="mt-5">
                    <h4 className={cn(SECTION_LABEL, "mb-2")}>Evidence</h4>
                    {files.length > 0 ? (
                        <ul className="m-0 grid list-none gap-2 p-0">
                            {files.map((file) => (
                                <li key={file.id} className="rounded-lg border border-[#26364e] bg-[#0c1828] p-2.5">
                                    <div className="flex items-center gap-2.5">
                                        <FileText className="size-4 shrink-0 text-[#94a3b8]" />
                                        <span className="min-w-0 flex-1 truncate text-sm">{file.file_name}</span>
                                        {file.quarantine_status === "failed" && (
                                            <button
                                                type="button"
                                                disabled={retrying !== null}
                                                onClick={() => void handleRetry(file.id)}
                                                title="Run the security check again"
                                                className="grid size-7 shrink-0 place-items-center rounded-md border border-brand-panel-border text-[#cbd5e1] hover:border-brand-cyan/50 hover:text-brand-cyan disabled:opacity-50"
                                            >
                                                <RotateCcw className={cn("size-3.5", retrying === file.id && "animate-spin")} />
                                            </button>
                                        )}
                                        <button
                                            type="button"
                                            disabled={file.quarantine_status !== "clean"}
                                            onClick={() => void handleDownload(file.id, file.file_name)}
                                            title={file.quarantine_status === "clean" ? "Download" : "Available once the security check passes"}
                                            aria-label={`Download ${file.file_name}`}
                                            className="grid size-7 shrink-0 place-items-center rounded-md border border-brand-panel-border text-[#cbd5e1] hover:border-brand-cyan/50 hover:text-brand-cyan disabled:cursor-not-allowed disabled:opacity-40"
                                        >
                                            <Download className="size-3.5" />
                                        </button>
                                    </div>
                                    <span className={cn("mt-2 inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold", EVIDENCE_PILL[file.quarantine_status] ?? EVIDENCE_PILL.pending)}>
                                        {evidenceStatusLabel(file.quarantine_status)}
                                    </span>
                                    {file.scan_message && <p className="m-0 mt-1 text-[11px] text-[#94a3b8]">{file.scan_message}</p>}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className="m-0 rounded-lg border border-dashed border-brand-panel-border px-3 py-4 text-center text-sm text-muted-foreground">
                            No evidence attached yet.
                        </p>
                    )}
                </section>

                {notice && (
                    <p role="status" className="m-0 mt-3 text-sm text-brand-alert">{notice}</p>
                )}
            </div>
        </SidePanelShell>
    );
}