"use client"

import { Button } from "@/components/ui/button";
import ServiceDeliveryModal from "@/shared/components/ServiceDeliveryModal";
import { downloadBlob, formatLabel, severityClass, whiteOutlineButtonClass } from "@/lib/serviceDeliveryUi";
import { downloadEvidence } from "@/lib/serviceDeliveryService";
import type { FindingDetail } from "@/lib/serviceDeliveryTypes";

export default function FindingInspectModal({ finding, onClose }: { finding: FindingDetail; onClose: () => void }) {
    const files = finding.evidence_files;

    async function handleDownload(evidenceId: string, fileName: string) {
        const blob = await downloadEvidence(evidenceId, fileName);
        downloadBlob(fileName, blob);
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
                                <div className="text-[11px] text-brand-text/70">Attached evidence</div>
                            </div>
                            <Button variant="outline" size="sm" className={whiteOutlineButtonClass} onClick={() => handleDownload(file.id, file.file_name)}>Download</Button>
                        </div>
                    ))}
                </div>
            ) : (
                <p className="text-sm text-brand-text/70">No evidence is attached to this finding.</p>
            )}

            <p className="mt-4 text-sm text-brand-text/70">
                Service Delivery inspects the finding for quality and report readiness
            </p>

            <div className="mt-5 flex justify-end">
                <Button variant="outline" size="sm" className={whiteOutlineButtonClass} onClick={onClose}>Close</Button>
            </div>
        </ServiceDeliveryModal>
    );
}



