"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import ServiceDeliveryPageTitle from "@/shared/components/ServiceDeliveryPageTitle";
import FindingInspectModal from "@/shared/components/FindingInspectModal";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { downloadEvidence, getEngagementDetail, getEngagementFinding, listEngagementFindings } from "@/lib/serviceDeliveryService";
import type { EngagementDetail, FindingDetail, FindingListItem, FindingStatus, Severity } from "@/lib/serviceDeliveryTypes";
import { controlFieldClass, downloadBlob, downloadTextFile, formatLabel, severityClass, whiteOutlineButtonClass } from "@/lib/serviceDeliveryUi";

const SEVERITY_OPTIONS: Severity[] = ["critical", "high", "medium", "low", "info"];
const STATUS_OPTIONS: FindingStatus[] = ["open", "in_progress", "resolved", "accepted_risk", "false_positive"];
const PAGE_SIZE = 12;

export default function EngagementFindingsPage() {
    const params = useParams<{ id:string }>();
    const [engagement, setEngagement] = useState<EngagementDetail | null>(null);
    const [findings, setFindings] = useState<FindingListItem[]>([]);
    const [total, setTotal] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [severity, setSeverity] = useState<Severity | "all">("all");
    const [status, setStatus] = useState<FindingStatus | "all">("all");
    const [page, setPage] = useState(1);
    const [inspectFinding, setInspectFinding] = useState<FindingDetail | null>(null);

    useEffect(() => {
        getEngagementDetail(params.id).then(setEngagement).catch(console.error);
    }, [params.id]);
    useEffect(() => {
        setIsLoading(true);
        listEngagementFindings(params.id, {
            severity: severity === "all" ? undefined : severity,
            status: status ==="all" ? undefined : status,
            limit: PAGE_SIZE,
            offset: (page - 1) * PAGE_SIZE,
        })
            .then((res) => {
                setFindings(res.items);
                setTotal(res.pagination.total);
            })
            .catch(console.error)
            .finally(() => setIsLoading(false));
    }, [params.id, severity, status, page]);

    const query = search.trim().toLowerCase();
    const visibleRows = query ? findings.filter((f) =>f.title.toLowerCase().includes(query)) : findings;

    async function openFinding(findingId: string) {
        const detail = await getEngagementFinding(params.id, findingId);
        setInspectFinding(detail);
    }

    async function downloadFindingEvidence(f: FindingListItem) {
        const detail = await getEngagementFinding(params.id, f.id);
        const firstFile = detail.evidence_files[0];
        if (firstFile) {
            const blob = await downloadEvidence(firstFile.id, firstFile.file_name);
            downloadBlob(firstFile.file_name, blob);
            return;
        }
        downloadTextFile(
            `${f.title.replace(/\s+/g, "-").toLowerCase()}.txt`,
            `PenFlow Finding\n\n${f.title}\nAsset: ${f.asset_identifier ?? "-"}\nSeverity:
             ${formatLabel(f.severity)}\nStatus: ${formatLabel(f.status)}\n\nNo evidence file is attached to this finding.`,
        );
    }

    if (!engagement) {
        return (
            <>
                <ServiceDeliveryPageTitle title="Findings" />
                <p className="mt-6 text-sm text-brand-text/70">Loading findings…</p>
            </>
        );
    }

    const pages = Math.max(1, Math.ceil(total /PAGE_SIZE));

    return (
        <>
            <div className="flex items-center gap-2 text-xs text-brand-text/70">
                <Link href={`/service-delivery/engagements/${engagement.id}`} className="text-brand-cyan hover:underline">Engagement</Link>
                <span>›</span>
                <span>Findings</span>
            </div>

            <ServiceDeliveryPageTitle title={`${engagement.title} · Findings`} />
            <p className="mt-2 text-sm text-brand-text/80">Inspect large finding sets without crowding the engagement overview.</p>

            

            {inspectFinding && (
                <FindingInspectModal finding={inspectFinding} onClose={() => setInspectFinding(null)} />
            )}
        </>
    );
}

function StatChip({ label, value }: { label: string; value: number }) {
    return (
        <span className="rounded-md border border-brand-panel-border bg-brand-panel-deep px-2.5 py-1 text-xs text-brand-text/90">
            <b className="text-brand-text">{value}</b> {label}
        </span>
    );
}
