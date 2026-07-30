"use client";
import { useEffect, useState} from "react";

import { fetchScanStatus, getReportPdfUrl, type RealTimeScanStatus} from "@/lib/scanService";

const scanTypeLabel: Record<string, string> = {
    active_vulnerability: "Active Vulnerability Scan",
    passive_ctem: "Passive Reconnaissance",
};

export default function ScanHeader({scanId}: {scanId: string}) {
    const [scan, setScan] = useState<RealTimeScanStatus | null>(null);
    useEffect(()=> {
        fetchScanStatus(scanId).then(setScan).catch(()=> setScan(null));
    }, [scanId]);

    const domain = scan?.domain ?? "...";
    const scanType = scan ? (scanTypeLabel[scan.scan_type] ?? scan.scan_type) : "";

    return (
        <header className="flex items-start justify-between gap-6">
            <div>
                <div className="flex items-center gap-3">
                    <h1 className="m-0 text-[28px] text-foreground">{domain}</h1>
                    {scan && (
                        <span className="rounded-full border border-brand-success/60 bg-brand-success/10 px-2.5 py-1 text-[10px] font-bold text-brand-success uppercase capitalize">
                            {scan.status}
                        </span>
                    )}
                </div>
                <p className="mt-2.5 flex items-center gap-2 text-sm text-muted-foreground">
                    <span>{scanType}</span>
                </p>
            </div>

                

                <div className="flex items-center gap-4.5">
                    <a
                        href={getReportPdfUrl(scanId)}
                        target="_blank"
                        rel = "noopener noreferrer"
                        className="min-h-[42px] rounded-lg border-brand-panel-border bg-brand-panel-deep px-4 py-2.5 text-foreground hover:bg-brand-panel"
                    >
                        Download
                    </a>
                        <button
                            type = "button" 
                            className="min-h-[42px] w-[42px] rounded-lg border border-brand-panel-border bg-brand-panel-deep p-0 text-xl text-foreground hover:bg-brand-panel"
                            aria-label="More actions"
                        >
                            :
                        </button>
                        </div>
                        </header>

    );  
}

