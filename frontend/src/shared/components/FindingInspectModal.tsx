"use client"

import { Button } from "@/components/ui/button";
import ServiceDeliveryModal from "@/shared/components/ServiceDeliveryModal";
import { downloadBlob, formatLabel, severityClass, whiteOutlineButtonClass } from "@/lib/serviceDeliveryUi";
import { downloadEvidence } from "@/lib/serviceDeliveryService";
import type { FindingDetail } from "@/lib/serviceDeliveryTypes";

export default function FindingInspectModal({ finding, onClose }: { finding: FindingDetail; onClose: () => void }) {
    const blob = finding.evidence_files;

    async function handleDownload(evidenceId: string, fileName: string) {
        const blob = await downloadEvidence(evidenceId, fileName);
        downloadBlob(fileName, blob)
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
            
        </ServiceDeliveryModal>
    );
}



