"use client"

import { Button } from "@/components/ui/button";
import ServiceDeliveryModal from "@/shared/components/ServiceDeliveryModal";
import { downloadBlob, formatLabel, severityClass, whiteOutlineButtonClass } from "@/lib/serviceDeliveryUi";
import type { FindingDetail } from "@/lib/serviceDeliveryTypes";
import { useState } from "react";
import { evidenceStatusLabel } from "@/lib/evidenceQuarantine";
import {
    downloadEvidence,
    retryEvidenceSecurityCheck,
} from "@/lib/serviceDeliveryService";

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
            setNotice(
                error instanceof Error
                    ? error.message
                    : "Unable to download evidence.",
            );
        }
    }

    async function handleRetry(evidenceId: string) {
        setRetrying(evidenceId);
        setNotice("");

        try {
            const updated = await retryEvidenceSecurityCheck(evidenceId);

            setFiles((current) =>
                current.map((file) =>
                    file.id === updated.id ? updated : file,
                ),
            );
            setNotice("Check queued. Reopen this finding to refresh its status.");
        } catch (error) {
            setNotice(
                error instanceof Error
                    ? error.message
                    : "Unable to retry the security check.",
            );
        } finally {
            setRetrying(null);
        }
    }

    return(
        <ServiceDeliveryModal kicker="Finding inspection" title={finding.title} onClose={onClose} maxWidthClassName="max-w-lg">
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                <p><b className="text-brand-text">Asset:</b><span className="text-brand-text/90">{finding.asset_identifier ?? "-"}</span></p>
                 <p><b className="text-brand-text">Source:</b> <span className="text-brand-text/90">{finding.source}</span></p>
                <p><b className="text-brand-text">Severity:</b> <span className={severityClass[finding.severity]}>{formatLabel(finding.severity)}</span></p>
                <p><b className="text-brand-text">Status:</b> <span className="text-brand-text/90">{formatLabel(finding.status)}</span></p> 
            </div>

            {finding.description && (
                <>
                    <h3 className="mt-4 mb-2 text-xs font-semibold tracking-wide text-brand-text/70 uppercase">Description</h3>
                    <p className="text-sm text-brand-text/90">{finding.description}</p>
                </>
            )}

            {finding.recommendation && (
                <>
                    <h3 className="mt-4 mb-2 text-xs font-semibold tracking-wide text-brand-text/70 uppercase"> Recommendation</h3>
                    <p className="text-sm text-brand-text/90">{finding.recommendation}</p>
                </>
            )}

            <h3 className="mt-4 mb-2 text-xs font-semibold tracking-wide text-brand-text/70 uppercase">Evidence</h3>
            {files.length > 0 ? (
                <div className="space-y-2">
                    {files.map((file) => (
                        <div key={file.id} className="flex items-center justify-between gap-3 rounded-md border border-brand-panel-border bg-brand-panel-deep p-3">
                            <div>
                                <div className="text-sm font-semibold text-brand-text">{file.file_name}</div>
                                <div className="text-[11px] text-brand-text/70">
                                    {evidenceStatusLabel(file.quarantine_status)}
                                </div>
                                {file.scan_message && (
                                    <div className="text-[11px] text-brand-text/70">
                                        {file.scan_message}
                                    </div>
                                )}
                            </div>
                            <div className="flex gap-2">
                                {file.quarantine_status === "failed" && (
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className={whiteOutlineButtonClass}
                                        disabled={retrying !== null}
                                        onClick={() => handleRetry(file.id)}
                                    >
                                        {retrying === file.id ? "Queuing…" : "Retry check"}
                                    </Button>
                                )}
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className={whiteOutlineButtonClass}
                                    disabled={file.quarantine_status !== "clean"}
                                    onClick={() => handleDownload(file.id, file.file_name)}
                                >
                                    Download
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <p className="text-sm text-brand-text/70">No evidence is attached to this finding.</p>
            )}

            <p className="mt-4 text-sm text-brand-text/70">
                Service Delivery inspects the finding for quality and report readiness
            </p>

            <p className="mt-3 text-xs text-brand-text/70">
                Security checks run in the background. Reopen this finding to refresh.
            </p>
            {notice && (
                <p role="status" className="mt-2 text-sm text-brand-text/80">
                    {notice}
                </p>
            )}
            
            <div className="mt-5 flex justify-end">
                <Button variant="outline" size="sm" className={whiteOutlineButtonClass} onClick={onClose}>Close</Button>
            </div>
        </ServiceDeliveryModal>
    );
}



