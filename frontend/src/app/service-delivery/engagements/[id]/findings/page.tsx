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

            <Card className="mt-6 border-brand-panel-border bg-brand-panel">
                <CardContent>
                    <div className="flex flex-wrap gap-3">
                        <Input
                            placeholder="Search findings on this page..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className={cn("min-w-[240px] flex-1", controlFieldClass)}
                        />
                        <Select value={severity} onValueChange={(v) => { setSeverity(v as Severity | "all"); setPage(1); }}>
                            <SelectTrigger className={cn("w-[170px]", controlFieldClass)}><SelectValue placeholder="All severities" /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All severities</SelectItem>
                                {SEVERITY_OPTIONS.map((s) => (
                                    <SelectItem key={s} value={s}>{formatLabel(s)}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <Select value={status} onValueChange={(v) => { setStatus(v as FindingStatus | "all"); setPage(1); }}>
                            <SelectTrigger className={cn("w-[170px]", controlFieldClass)}><SelectValue placeholder="All statuses" /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All statuses</SelectItem>
                                {STATUS_OPTIONS.map((s) => (
                                    <SelectItem key={s} value={s}>{formatLabel(s)}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                        <StatChip label="total" value={engagement.finding_summary.total} />
                        <StatChip label="critical" value={engagement.finding_summary.critical} />
                        <StatChip label="high" value={engagement.finding_summary.high} />
                        <StatChip label="medium" value={engagement.finding_summary.medium} />
                        <StatChip label="low" value={engagement.finding_summary.low} />
                        <StatChip label="with evidence" value={engagement.finding_summary.with_evidence} />
                    </div>

                    <div className="mt-4 overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead>
                                <tr className="text-[11px] text-brand-text/70">
                                    <th className="pb-2 font-medium">Finding</th>
                                    <th className="pb-2 font-medium">Asset</th>
                                    <th className="pb-2 font-medium">Source</th>
                                    <th className="pb-2 font-medium">Severity</th>
                                    <th className="pb-2 font-medium">Status</th>
                                    <th className="pb-2 font-medium">Verified</th>
                                    <th className="pb-2 font-medium" />
                                    <th className="pb-2 font-medium" />
                                </tr>
                            </thead>
                            
                        </table>
                    </div>

                    <div className="mt-4 flex items-center justify-between text-sm text-brand-text/70">
                        <Button variant="outline" size="sm" className={whiteOutlineButtonClass} disabled={page === 1} onClick={() => setPage((p) => p - 1)}>← Previous</Button>
                        <span>Page {page} of {pages} · {total} findings</span>
                        <Button variant="outline" size="sm" className={whiteOutlineButtonClass} disabled={page === pages} onClick={() => setPage((p) => p + 1)}>Next →</Button>
                    </div>
                </CardContent>
            </Card>
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
