"use client";

import { useEffect, useMemo, useState} from "react";

import { fetchScanFindings, type DashboardFindingItem } from "@/lib/scanService";
import { capitalize, cn } from "@/lib/utils";

type SortOption = "severity" | "cvss" | "asset" | "title";

const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };

const summaryCardClassName: Record<string, string> = {
    critical: "border-[#991b1b] [&>span]:text-[#ef4444]",
    high: "border-[#a34908] [&>span]:text-[#f97316]",
    medium: "border-[#8a6a00] [&>span]:text-[#facc15]",
    low: "border-[#18549a] [&>span]:text-brand-cyan",
};

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

const FILTER_LABEL_CLASS_NAME = "flex min-h-[46px] items-center gap-2.5 rounded-lg border border-brand-panel-border bg-[#0b1625] px-3.5";
const TAG_CLASS_NAME = "max-w-full overflow-hidden text-ellipsis whitespace-nowrap rounded-[5px] border border-[#26364e] bg-[#091523] px-2 py-1 text-[10px] text-[#9eacbd]";
const CONTEXT_BOX_CLASS_NAME = "grid gap-1 rounded-[7px] border border-[#26364e] bg-[#0c1828] p-2.5";

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
    const [findings, setFindings] = useState<DashboardFindingItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [severityFilter, setSeverityFilter] = useState<string>("all");
    const [sort, setSort] = useState<SortOption>("severity");
    const [selectedFinding, setSelectedFinding] = useState<DashboardFindingItem | null>(null);

    useEffect(() => {
        setLoading(true);
        fetchScanFindings(scanId, { limit: 100 })
            .then((result: DashboardFindingItem[]) => {
                setFindings(result);
                setSelectedFinding(result[0] ?? null);
            })
            .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load findings"))
            .finally(() => setLoading(false));
    }, [scanId]);

    const severityCounts = useMemo(() => {
        const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0};
        for (const finding of findings) {
            const key = finding.severity.toLowerCase();
            if (key in counts) counts[key] += 1;
        }
        return counts;
    }, [findings]);

    const visibleFindings = useMemo(() => {
        const filtered = findings
            .filter((f) => severityFilter === "all" || f.severity.toLowerCase() === severityFilter)
            .filter((f) => f.title.toLowerCase().includes(search.trim().toLowerCase()));
        return sortFindings(filtered, sort);
    }, [findings, severityFilter, search, sort]);

    return (
        <section className="min-w-0 pt-6" data-scan-id={scanId}>
            <div className="mb-5 grid grid-cols-[minmax(160px,0.7fr)_minmax(520px,1.55fr)_minmax(330px,1fr)] items-center gap-7 max-[1450px]:grid-cols-[auto_minmax(500px,1fr)] max-[1100px]:flex max-[1100px]:flex-col max-[1100px]:items-stretch">
                <div>
                    <div className="flex items-center gap-2.5">
                        <h2 className="m-0 text-[25px] text-foreground">Findings</h2>
                        <span className="rounded-full bg-[#172338] px-2.5 py-1 text-[13px] text-[#dbeafe]">{findings.length}</span>
                    </div>
                    <p className="mt-2 text-[13px] text-muted-foreground">
                        Across {new Set(findings.map((f) => f.asset_identifier).filter(Boolean)).size} assets
                    </p>
                </div>

                <div className="grid grid-cols-4 gap-3 max-[1100px]:grid-cols-2 max-[720px]:grid-cols-1">
                    {(["critical", "high", "medium", "low"] as const).map((severity) => (
                        <div
                            key={severity}
                            className={cn(
                                "rounded-[9px] border bg-[#0b1625] p-3.5 text-left text-foreground",
                                summaryCardClassName[severity]
                            )}
                        >
                            <span className="mb-2.5 block text-xs">{capitalize(severity)}</span>
                            <div className="flex items-baseline gap-2.5">
                                <strong className="text-[25px]">{severityCounts[severity]}</strong>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="grid gap-2.5 max-[1450px]:col-span-full max-[1450px]:grid-cols-[1fr_320px] max-[1100px]:grid-cols-1">
                    <label className={FILTER_LABEL_CLASS_NAME}>
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
                </div>
            </div>

            {error && <p className="mt-4 text-xs text-muted-foreground">{error}</p>}
            {loading && <p className="mt-4 text-xs text-muted-foreground">Loading findings...</p>}

            {!loading && !error && (
                <div
                    className={cn(
                        "grid items-start gap-4.5",
                        selectedFinding
                            ? "grid-cols-[minmax(0,1fr)_510px] max-[1450px]:grid-cols-[minmax(0,1fr)_390px] max-[1100px]:grid-cols-1"
                            : "grid-cols-[minmax(0,1fr)]"
                    )}
                >
                    <div className="min-w-0">
                        {visibleFindings.length === 0 ?(
                            <p className="mt-4 text-xs text-muted-foreground">No findings match your filters.</p>
                        ) : (
                            <div className="grid grid-cols-3 gap-3.5 max-[1450px]:grid-cols-2 max-[720px]:grid-cols-1">
                                {visibleFindings.map((finding) => {
                                    const severity = finding.severity.toLowerCase();
                                    const isSelected = selectedFinding?.id === finding.id;

                                    return(
                                        <button
                                            key={finding.id}
                                            type="button"
                                            onClick={() => setSelectedFinding(finding)}
                                            className={cn(
                                                "flex min-h-[176px] min-w-0 flex-col rounded-[9px] border bg-[#0b1625] p-3.5 text-left text-foreground hover:bg-[#101e30]",
                                                findingCardBorderClassName[severity],
                                                isSelected && "shadow-[0_0_0_1px_currentColor,0_0_24px_rgb(56_166_255/0.08)]"
                                            )}
                                        >
                                            <div className="flex items-start justify-between gap-2.5">
                                                <div className="flex min-w-0 items-start gap-2.5">
                                                    <span
                                                        className={cn(
                                                            "grid h-[25px] w-[22px] shrink-0 place-items-center rounded-[7px] border-2 text-[11px] font-bold",
                                                            findingIconClassName[severity]
                                                        )}
                                                    >
                                                        !
                                                    </span>
                                                    <h3 className="mt-px text-[13px] leading-[1.35]">{finding.title}</h3>
                                                </div>

                                                <SeverityBadge severity={severity} label={finding.severity} />
                                            </div>

                                            {finding.description && (
                                                <p className="my-3 line-clamp-2 min-h-[42px] text-xs leading-normal text-[#b4c0cf]">
                                                    {finding.description}        
                                                </p>
                                            )}

                                            <div className="flex flex-wrap gap-2">
                                                {finding.asset_identifier && (
                                                    <span className={TAG_CLASS_NAME}>{finding.asset_identifier}</span>
                                                )}
                                                <span className={TAG_CLASS_NAME}>{finding.source}</span>
                                                {finding.cve_id && <span className={TAG_CLASS_NAME}>{finding.cve_id}</span>}
                                            </div>

                                            <div className="mt-auto flex items-center gap-2.5 pt-3.5 text-[10px] text-muted-foreground">
                                                <span>CVSS {finding.cvss_score ?? "-"}</span>
                                                <span className="text-xl text-foreground" aria-hidden="true">›</span>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {selectedFinding && (
                        <FindingDetails
                            finding={selectedFinding}
                            onClose={() => setSelectedFinding(null)}
                        />
                    )}
                </div>
            )}
        </section>
    );
}

function FindingDetails({
    finding,
    onClose,
}: {
    finding: DashboardFindingItem;
    onClose: () => void;
}) {
    const severity = finding.severity.toLowerCase();
    return (
        <aside className="min-w-0 overflow-hidden rounded-[10px] border border-brand-panel-border bg-[#0b1625] max-[1100px]:static max-[1100px]:max-h-none lg:sticky lg:top-5 lg:max-h-[calc(100vh-40px)]">
            <header className="flex items-start justify-between gap-3 p-[18px]">
                <div>
                    <div className="flex items-start gap-2.5">
                        <h2 className="m-0 text-lg leading-[1.3]">{finding.title}</h2>
                        <SeverityBadge severity={severity} label={finding.severity} />
                    </div>

                    <p className="mt-2.5 flex gap-2 text-[11px] text-muted-foreground">
                        {finding.cve_id ?? "No reference"}
                        <span>•</span>
                        <strong className="text-[#ef4444]">CVSS {finding.cvss_score ?? "-"}</strong>
                    </p>
                </div>

                <button
                    type="button"
                    onClick={onClose}
                    aria-label="Close finding details"
                    className="border-0 bg-transparent text-2xl text-muted-foreground"
                >
                    ×
                </button>
            </header>

            <div className="max-h-[calc(100vh-255px)] overflow-y-auto p-[18px] max-[1100px]:max-h-none">
                <section className="border-b border-brand-panel-border pb-[18px]">
                    <h3 className="m-0 mb-2.5 text-[11px] uppercase">Description</h3>
                    <p className="m-0 text-[11px] leading-[1.65] text-[#abb7c7]">
                        {finding.description ?? "No description available."}
                    </p>
                </section>

                <section className="border-b border-brand-panel-border pt-[18px] pb-[18px]">
                    <h3 className="m-0 mb-2.5 text-[11px] uppercase">Recommendations</h3>
                    <p className="m-0 text-[11px] leading-[1.65] text-[#abb7c7]">
                        {finding.recommendation ?? "No recommendation available."}
                    </p>
                </section>

                <section className="pt-[18px]">
                    <h3 className="m-0 mb-2.5 text-[11px] uppercase">Context</h3>
                    <dl className="m-0 grid grid-cols-2 gap-3 max-[720px]:grid-cols-1">
                        <div className={CONTEXT_BOX_CLASS_NAME}>
                            <dt className="text-[9px] text-muted-foreground">Source</dt>
                            <dd className="m-0 [overflow-wrap:anywhere] text-[10px] text-[#d1dae6]">{finding.source}</dd>
                        </div>
                        {finding.asset_identifier && (
                            <div className={CONTEXT_BOX_CLASS_NAME}>
                                <dt className="text-[9px] text-muted-foreground">Affected Asset</dt>
                                <dd className="m-0 [overflow-wrap:anywhere] text-[10px] text-[#d1dae6]">{finding.asset_identifier}</dd>
                            </div>
                        )}
                    </dl>
                </section>
            </div>
        </aside>
    );
}
