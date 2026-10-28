"use client";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState} from "react";
import { ChevronRight, X } from "lucide-react";

import { fetchScanFindings, type DashboardFindingItem } from "@/lib/scanService";
import { capitalize, cn } from "@/lib/utils";
import { Bug } from "lucide-react";
import { FilterSheet } from "@/shared/components/DetailSheet";
import { FINDINGS_COLORS, SummaryCard } from "./SummaryCard";
import SidePanelShell from "@/shared/components/SidePanelShell";

type SortOption = "severity" | "cvss" | "asset" | "title";

const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };

const findingCardBorderClassName: Record<string, string> = {
    critical: "border-[#c82029]",
    high: "border-[#d26600]",
    medium: "border-[#b99500]",
    low: "border-[#1f68b4]",
};

const findingIconClassName: Record<string, string> = {
    critical: "border-[#ef4444] text-[#ef4444]",
    high: "border-[#f97316] text-[#f97316]",
    medium: "border-[#facc15] text-[#facc15]",
    low: "border-[#3b82f6] text-[#3b82f6]",
};

const severityBadgeClassName: Record<string, string> = {
    critical: "border-[#991b1b] text-[#ef4444] bg-[#991b1b]/[0.08]",
    high: "border-[#a34908] text-[#f97316] bg-[#8a6a00]/[0.08]",
    medium: "border-[#8a6a00] text-[#facc15] bg-[#8a6a00]/[0.08]",
    low: "border-[#18549a] text-[#60a5fa] bg-[#18549a]/[0.08]"
};

const FINDING_STRIPE_CLASS_NAME: Record<string, string> = {
    critical: "border-l-[#ef4444]",
    high: "border-l-[#f97316]",
    medium: "border-l-[#facc15]",
    low: "border-l-[#60a5fa]",
    info: "border-l-[#64748b]",
};

const FILTER_LABEL_CLASS_NAME = "flex min-h-10 items-center gap-2.5 rounded-lg border border-brand-panel-border bg-[#0b1625] px-3.5";
const TAG_CLASS_NAME = "max-w-full overflow-hidden text-ellipsis whitespace-nowrap rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-1 text-[10px] text-[#9eacbd]";

function SeverityBadge({ severity, label }: { severity: string; label: string}) {
    return (
        <span
            className={cn(
                "w-fit shrink-0 rounded-[5px] border px-2 py-1 text-[9px] font-bold uppercase",
                severityBadgeClassName[severity]
            )}
        >
            {label}
        </span>
    );
}

function sortFindings(findings: DashboardFindingItem[], sort: SortOption): DashboardFindingItem[] {
    const copy = [...findings];
    switch (sort) {
        case "severity":
            return copy.sort((a, b) => (severityOrder[a.severity.toLowerCase()] ?? 99) - (severityOrder[b.severity.toLowerCase()] ?? 99));
        case "cvss":
            return copy.sort((a, b) => (b.cvss_score ?? 0) - (a.cvss_score ?? 0));
        case "asset":
            return copy.sort((a, b) => (a.asset_identifier ?? "").localeCompare(b.asset_identifier ?? ""));
        case "title":
            return copy.sort((a, b) => a.title.localeCompare(b.title));
        default:
            return copy;
    }
}

export default function FindingsGrid({ scanId }: { scanId: string }) {
    const searchParams = useSearchParams();
    const router = useRouter();
    const pathname = usePathname();
    const assetFilter = searchParams.get("asset") ?? "";
    const clearAssetFilter = () => {
        const params = new URLSearchParams(searchParams.toString());
        params.delete("asset");
        const query = params.toString();
        router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    };
    const findingFilter = searchParams.get("finding") ?? "";

    const [findings, setFindings] = useState<DashboardFindingItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [severityFilter, setSeverityFilter] = useState<string>("all");
    const [sort, setSort] = useState<SortOption>("severity");
    const [selectedFinding, setSelectedFinding] = useState<DashboardFindingItem | null>(null);
    const closeFinding = useCallback(() => setSelectedFinding(null), []);

    useEffect(() => {
        setLoading(true);
        fetchScanFindings(scanId, { limit: 100 })
            .then((result: DashboardFindingItem[]) => {
                setFindings(result);

            })
            .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load findings"))
            .finally(() => setLoading(false));
    }, [scanId]);

    useEffect(() => {
        if(!findingFilter) {
            return;
        }

        const requestedFinding = findings.find(
            (finding) => finding.id === findingFilter,
        );

        if(requestedFinding) {
            setSelectedFinding(requestedFinding);
        }
    }, [findingFilter, findings]);

    const severityCounts = useMemo(() => {
        const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
        for (const finding of findings) {
            const key = finding.severity.toLowerCase();
            if (key in counts) counts[key] += 1;
        }
        return counts;
    }, [findings]);

    const visibleFindings = useMemo(() => {
        const filtered = findings
            .filter((f) => severityFilter === "all" || f.severity.toLowerCase() === severityFilter)
            .filter((f) => !assetFilter || f.asset_identifier === assetFilter)
            .filter((f) => f.title.toLowerCase().includes(search.trim().toLowerCase()));
        return sortFindings(filtered, sort);
    }, [findings, severityFilter, search, sort, assetFilter]);

    return (
        <section className="min-w-0 pt-6" data-scan-id={scanId}>
            <div className="mb-5 grid grid-cols-[max-content_max-content_minmax(400px,1fr)] items-center gap-7 max-[1450px]:grid-cols-[auto_minmax(500px,1fr)] max-[1100px]:flex max-[1100px]:flex-col max-[1100px]:items-stretch">
                <div>
                    <div className="flex items-center gap-2.5">
                        <h2 className="m-0 text-[25px] text-foreground">Findings</h2>
                        <span className="rounded-full bg-[#172338] px-2.5 py-1 text-[13px] text-[#dbeafe]">{findings.length}</span>
                    </div>
                    <p className="mt-2 text-[13px] text-muted-foreground">
                        Across {new Set(findings.map((f) => f.asset_identifier).filter(Boolean)).size} assets
                    </p>
                    {assetFilter && (
                        <button
                            type="button"
                            onClick={clearAssetFilter}
                            aria-label={`Clear asset filter ${assetFilter} and show all findings`}
                            title="Show all findings"
                            className="mt-2 inline-flex max-w-full items-center gap-1.5 rounded-full border border-brand-cyan/50 bg-brand-cyan/10 py-0.5 pr-1.5 pl-2.5 text-[11px] text-brand-cyan hover:bg-brand-cyan/20"
                        >
                            <span className="text-[#94a3b8]">Asset:</span>
                            <span className="truncate font-semibold">{assetFilter}</span>
                            <X className="size-3.5 shrink-0" aria-hidden="true" />
                        </button>
                    )}
                </div>

                <SummaryCard
                    title="Findings"
                    icon={Bug}
                    accentClassName="bg-brand-alert/10 text-brand-alert"
                    value={findings.length}
                    items={(["critical", "high", "medium", "low", "info"] as const).map((severity) => ({ label: capitalize(severity), value: severityCounts[severity] }))}
                    colors={[FINDINGS_COLORS.critical, FINDINGS_COLORS.high, FINDINGS_COLORS.medium, FINDINGS_COLORS.low, FINDINGS_COLORS.info]}
                    keepBreakdownOnPhones
                    layout="side"
                    className="w-fit border"
                />

                <div className="grid w-full max-w-[760px] grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)] gap-2 justify-self-end max-[1450px]:col-span-full max-[1450px]:max-w-none max-[1450px]:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)] max-[1100px]:grid-cols-1 max-[720px]:grid-cols-[minmax(0,1fr)_auto]">
                    <label className={cn(FILTER_LABEL_CLASS_NAME, "col-span-2 max-[1450px]:col-span-1")}>
                        <span aria-hidden="true" className="text-[19px] text-muted-foreground">⌕</span>
                        <input
                            type="search"
                            placeholder="Search findings..."
                            aria-label="Search findings"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                                className="w-full border-0 bg-transparent text-foreground outline-none"
                        />
                    </label>

                    <FilterSheet activeCount={Number(sort !== "severity") + Number(severityFilter !== "all")}>
                    <label className={FILTER_LABEL_CLASS_NAME}>
                        <span className="shrink-0 border-r border-brand-panel-border pr-3 text-xs text-muted-foreground">Sort by</span>
                        <select
                            value={sort}
                            onChange={(e) => setSort(e.target.value as SortOption)}
                            className="w-full border-0 bg-[#0b1625] text-[#cbd5e1] outline-none"
                        >
                            <option value="severity">Severity: High to Low</option>
                            <option value="cvss">CVSS Score</option>
                            <option value="asset">Affected Asset</option>
                            <option value="title">Finding Name</option>
                        </select>
                    </label>

                    <label className={FILTER_LABEL_CLASS_NAME}>
                        <span className="shrink-0 border-r border-brand-panel-border pr-3 text-xs text-muted-foreground">Severity</span>
                        <select
                            value={severityFilter}
                            onChange={(e) => setSeverityFilter(e.target.value)}
                            className="w-full border-0 bg-[#0b1625] text-[#cbd5e1] outline-none"
                        >
                            <option value="all">All</option>
                            <option value="critical">Critical</option>
                            <option value="high">High</option>
                            <option value="medium">Medium</option>
                            <option value="low">Low</option>
                            <option value="info">Info</option>
                        </select>
                    </label>
                    </FilterSheet>
                </div>
            </div>

            {error && <p className="mt-4 text-xs text-muted-foreground">{error}</p>}
            {loading && <p className="mt-4 text-xs text-muted-foreground">Loading findings...</p>}

            {!loading && !error && (
                <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-4.5">
                    <div className="min-w-0">
                        {visibleFindings.length === 0 ?(
                            <p className="mt-4 text-xs text-muted-foreground">No findings match your filters.</p>
                        ) : (
                            <div className="grid grid-cols-3 gap-3.5 max-[1450px]:grid-cols-2 max-[720px]:grid-cols-1 max-[720px]:gap-2">
                                {visibleFindings.map((finding) => {
                                    const severity = finding.severity.toLowerCase();
                                    const isSelected = selectedFinding?.id === finding.id;
                                    const mobileMeta = [
                                        finding.asset_identifier,
                                        finding.source,
                                        finding.cvss_score != null ? `CVSS ${finding.cvss_score}` : null,
                                    ].filter(Boolean).join(" · ");

                                    return(
                                        <button
                                            key={finding.id}
                                            type="button"
                                            onClick={() => setSelectedFinding(finding)}
                                            className={cn(
                                                "flex min-w-0 flex-col rounded-[9px] border bg-[#0b1625] p-3 text-left text-foreground hover:bg-[#101e30]",
                                                findingCardBorderClassName[severity],
                                                "max-[720px]:min-h-0 max-[720px]:gap-1.5 max-[720px]:border-l-[3px] max-[720px]:border-y-brand-panel-border max-[720px]:border-r-brand-panel-border max-[720px]:p-3",
                                                isSelected && "shadow-[0_0_0_1px_currentColor,0_0_24px_rgb(56_166_255/0.08)]"
                                            )}
                                        >
                                            <div className="flex items-start justify-between gap-2.5">
                                                <div className="flex min-w-0 items-start gap-2.5">
                                                    <span
                                                        className={cn(
                                                            "grid h-[25px] w-[22px] shrink-0 place-items-center rounded-[7px] border-2 text-[11px] font-bold max-[720px]:hidden",
                                                            findingIconClassName[severity]
                                                        )}
                                                    >
                                                        !
                                                    </span>
                                                    <h3 className="mt-px text-[13px] leading-[1.35] max-[720px]:mt-0 max-[720px]:line-clamp-2 max-[720px]:text-sm max-[720px]:font-semibold max-[720px]:tracking-normal! max-[720px]:[font-family:inherit]!">{finding.title}</h3>
                                                </div>

                                                <SeverityBadge severity={severity} label={finding.severity} />
                                            </div>

                                            {finding.description && (
                                                <p className="my-2 line-clamp-1 text-xs leading-normal text-[#b4c0cf] max-[720px]:hidden">
                                                    {finding.description}        
                                                </p>
                                            )}

                                            <div className="mt-auto flex items-center justify-between gap-2 pt-1 max-[720px]:hidden">
                                                <div className="flex min-w-0 flex-wrap gap-1.5">
                                                    {finding.asset_identifier && (
                                                        <span className={TAG_CLASS_NAME}>{finding.asset_identifier}</span>
                                                    )}
                                                    <span className={TAG_CLASS_NAME}>{finding.source}</span>
                                                    {finding.cve_id && <span className={TAG_CLASS_NAME}>{finding.cve_id}</span>}
                                                </div>
                                                <span className="flex shrink-0 items-center gap-2 text-[10px] text-muted-foreground">
                                                    {finding.cvss_score != null && <span>CVSS {finding.cvss_score}</span>}
                                                    <span className="text-xl leading-none text-foreground" aria-hidden="true">›</span>
                                                </span>
                                            </div>
                                            <div className="hidden items-center justify-between gap-3 text-xs text-muted-foreground max-[720px]:flex">
                                                <span className="min-w-0 truncate">{mobileMeta}</span>
                                                <span className="text-lg leading-none text-foreground" aria-hidden="true">›</span>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {selectedFinding && (
                        <FindingDetails finding={selectedFinding} scanId={scanId} onClose={closeFinding} />
                    )}
                </div>
            )}
        </section>
    );
}

export function FindingDetails({
    finding,
    scanId,
    onClose,
    showViewInFindings = false,
}: {
    finding: DashboardFindingItem;
    scanId: string;
    onClose: () => void;
    showViewInFindings?: boolean;
}) {
    const severity = finding.severity.toLowerCase();
    const subtitle = [finding.source, finding.asset_identifier].filter(Boolean).join(" · ");
    return (
        <SidePanelShell labelledBy="finding-details-title" onClose={onClose}>
            <header className="flex items-start justify-between gap-3 border-b border-brand-panel-border p-4">
                <div className="min-w-0">
                    <h2 id="finding-details-title" className="m-0 text-base leading-snug font-semibold tracking-normal! text-foreground [font-family:inherit]!">
                        {finding.title}
                    </h2>
                    {subtitle && <p className="m-0 mt-0.5 text-[11px] break-all text-[#94a3b8]">{subtitle}</p>}
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        <SeverityBadge severity={severity} label={finding.severity} />
                        {finding.cvss_score !== null && finding.cvss_score !== undefined && (
                            <span className="rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-0.5 text-[10px] text-[#9eacbd]">CVSS {finding.cvss_score}</span>
                        )}
                        {finding.cve_id && (
                            <span className="rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-0.5 text-[10px] text-[#9eacbd]">{finding.cve_id}</span>
                        )}
                    </div>
                </div>
                <button type="button" onClick={onClose} aria-label="Close finding details"
                    className="grid size-8 shrink-0 place-items-center rounded-lg text-[#94a3b8] hover:bg-white/5 hover:text-foreground">
                    <X className="size-4" />
                </button>
            </header>

            <div className="min-h-0 overflow-y-auto overscroll-contain p-4">
                <article className={cn("rounded-lg border border-l-[3px] border-[#22324d] bg-[#0f1c30] p-4", FINDING_STRIPE_CLASS_NAME[severity])}>
                    {finding.asset_identifier && (
                        <p className="m-0 text-[11px] text-[#94a3b8]">Found on: {finding.asset_identifier}</p>
                    )}
                    <section className="mt-3">
                        <h4 className="m-0 mb-1 text-[10px] font-semibold tracking-wide text-[#94a3b8] uppercase">Description</h4>
                        <p className="m-0 text-[12px] leading-relaxed text-[#cbd5e1]">{finding.description ?? "No description available."}</p>
                    </section>
                    <section className="mt-3">
                        <h4 className="m-0 mb-1 text-[10px] font-semibold tracking-wide text-[#94a3b8] uppercase">How to fix</h4>
                        <p className="m-0 text-[12px] leading-relaxed text-[#cbd5e1]">{finding.recommendation ?? "No recommendation available."}</p>
                    </section>
                    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
                        {showViewInFindings && (
                            <Link
                                href={`/phase2_scan/results/${scanId}/findings?finding=${encodeURIComponent(finding.id)}`}
                                className="inline-flex items-center gap-1 text-[11px] font-semibold text-brand-cyan no-underline hover:underline"
                            >
                                View in findings <ChevronRight className="size-3.5" />
                            </Link>
                        )}
                        <Link
                            href={`/phase2_scan/results/${scanId}/graph?finding=${encodeURIComponent(finding.id)}`}
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-brand-cyan no-underline hover:underline"
                        >
                            View on graph <ChevronRight className="size-3.5" />
                        </Link>
                    </div>
                </article>
            </div>
        </SidePanelShell>
    );
}