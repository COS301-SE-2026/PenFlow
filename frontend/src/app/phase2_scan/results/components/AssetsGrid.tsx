"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ChevronRight, Network, X } from "lucide-react";

import {
    fetchScanAssets,
    fetchScanFindings,
    fetchScanGraph,
    type DashboardAssetItem,
    type DashboardFindingItem,
    type GraphNode,
    type ScanGraphResponse,
} from "@/lib/scanService";
import { capitalize, cn } from "@/lib/utils";
import { FilterSheet } from "@/shared/components/DetailSheet";
import SidePanelShell from "@/shared/components/SidePanelShell";
import { SummaryCard } from "./SummaryCard";
import { TYPE_COLOR, TypeBadge, isIpType, typeKey, typeLabel } from "./assetTypes";

type SortKey = "risk" | "name" | "type" | "ports" | "findings";
type SortDir = "asc" | "desc";
type ViewMode = "list" | "grouped";
type Severity = "critical" | "high" | "medium" | "low" | "info";

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"];
const SEVERITY_WEIGHT: Record<Severity, number> = { critical: 40, high: 20, medium: 8, low: 3, info: 1 };
const SEVERITY_TEXT: Record<Severity, string> = {
    critical: "text-[#ef4444]",
    high: "text-[#f97316]",
    medium: "text-[#facc15]",
    low: "text-[#60a5fa]",
    info: "text-[#94a3b8]",
};
const SEVERITY_BAR: Record<Severity, string> = {
    critical: "bg-[#ef4444]",
    high: "bg-[#f97316]",
    medium: "bg-[#facc15]",
    low: "bg-[#3b82f6]",
    info: "bg-[#64748b]",
};
const SEVERITY_BADGE: Record<Severity, string> = {
    critical: "border-[#991b1b] text-[#ef4444] bg-[#991b1b]/[0.08]",
    high: "border-[#a34908] text-[#f97316] bg-[#a34908]/[0.08]",
    medium: "border-[#8a6a00] text-[#facc15] bg-[#8a6a00]/[0.08]",
    low: "border-[#18549a] text-[#60a5fa] bg-[#18549a]/[0.08]",
    info: "border-[#334155] text-[#94a3b8] bg-[#334155]/[0.08]",
};

const CATEGORY_FOR_SOURCE: Record<string, string> = {
    http_security: "HTTP security headers",
    https_security: "HTTP security headers",
    tls: "TLS & certificates",
    cve: "Known vulnerabilities (CVEs)",
    hibp: "Data breaches",
    dns: "DNS & email",
};

const PAGE_SIZE = 100;
const selectClassName = "min-h-10 w-full rounded-lg border border-brand-panel-border bg-brand-panel-deep px-3 text-foreground outline-none";
const ROW_GRID = "grid grid-cols-[minmax(200px,1.4fr)_96px_minmax(140px,1fr)_120px_minmax(130px,1fr)_minmax(160px,auto)_16px] items-center gap-x-4";

async function fetchAll<T>(fetchPage: (offset: number) => Promise<T[]>): Promise<T[]> {
    const all: T[] = [];
    for (let offset = 0; offset < 5000; offset += PAGE_SIZE) {
        const page = await fetchPage(offset);
        all.push(...page);
        if (page.length < PAGE_SIZE) break;
    }
    return all;
}

interface PortInfo { id: string; port: string; name: string; product: string }
export interface AssetInsight {
    nodeId: string | null;
    related: { label: string; assetId: string | null }[];
    ports: PortInfo[];
    techs: string[];
}

export function buildInsights(graph: ScanGraphResponse | null, assets: DashboardAssetItem[]): Map<string, AssetInsight> {
    const insights = new Map<string, AssetInsight>();
    if (!graph) return insights;
    const nodesById = new Map(graph.nodes.map((n) => [n.id, n]));
    const domainNode = graph.nodes.find((n) => n.type === "domain");
    const outgoing = (id: string, type: string) => graph.edges.filter((e) => e.source === id && e.type === type).map((e) => e.target);
    const incoming = (id: string, type: string) => graph.edges.filter((e) => e.target === id && e.type === type).map((e) => e.source);
    const assetIdForNode = (node: GraphNode | undefined) => {
        if (!node) return null;
        if (node.type === "domain") return assets.find((a) => a.identifier === node.label)?.id ?? null;
        return node.entity_id;
    };

    for (const asset of assets) {
        const node = graph.nodes.find((n) => n.type === "asset" && n.entity_id === asset.id)
            ?? (domainNode && typeKey(asset.asset_type) === "subdomain" && asset.identifier === domainNode.label ? domainNode : undefined);
        if (!node) {
            insights.set(asset.id, { nodeId: null, related: [], ports: [], techs: [] });
            continue;
        }
        const ip = isIpType(asset.asset_type);
        const relatedIds = ip ? incoming(node.id, "RESOLVES_TO") : outgoing(node.id, "RESOLVES_TO");
        const related = relatedIds
            .map((id) => nodesById.get(id))
            .filter((n): n is GraphNode => Boolean(n))
            .map((n) => ({ label: n.label, assetId: assetIdForNode(n) }));
        const hostIds = ip ? [node.id] : [node.id, ...relatedIds];
        const serviceIds = [...new Set(hostIds.flatMap((id) => outgoing(id, "EXPOSES")))];
        const ports = serviceIds
            .map((id) => nodesById.get(id))
            .filter((n): n is GraphNode => Boolean(n))
            .map((svc) => ({
                id: svc.id,
                port: svc.metadata.port !== undefined && svc.metadata.port !== null ? `:${String(svc.metadata.port)}` : svc.label,
                name: svc.label.split(" :")[0] ?? "",
                product: [svc.metadata.product, svc.metadata.version].filter(Boolean).map(String).join(" "),
            }));
        const uniquePorts = [...new Map(ports.map((p) => [p.port, p])).values()]
            .sort((a, b) => Number(a.port.slice(1)) - Number(b.port.slice(1)));
        const techs = [...new Set([...serviceIds, ...hostIds].flatMap((id) => outgoing(id, "RUNS"))
            .map((id) => nodesById.get(id)?.label)
            .filter((label): label is string => Boolean(label)))].sort();
        insights.set(asset.id, { nodeId: node.id, related, ports: uniquePorts, techs });
    }
    return insights;
}

function severityCounts(findings: DashboardFindingItem[]): Record<Severity, number> {
    const counts: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    for (const f of findings) {
        const sev = f.severity.toLowerCase() as Severity;
        if (sev in counts) counts[sev] += 1;
    }
    return counts;
}
const riskScore = (counts: Record<Severity, number>) => SEVERITIES.reduce((n, s) => n + counts[s] * SEVERITY_WEIGHT[s], 0);

function FindingsSummary({ counts, total }: { counts: Record<Severity, number>; total: number }) {
    const present = SEVERITIES.filter((s) => counts[s] > 0);
    if (total === 0 || present.length === 0) return <span className="text-[11px] text-[#64748b]">No findings</span>;
    return (
        <span className="flex min-w-0 flex-col gap-1">
            <span className="flex flex-wrap gap-x-2 text-[11px] font-semibold">
                {present.map((s) => <span key={s} className={SEVERITY_TEXT[s]}>{counts[s]} {capitalize(s)}</span>)}
            </span>
            <span className="flex h-1 w-full max-w-[140px] overflow-hidden rounded-full bg-white/5">
                {present.map((s) => <span key={s} className={SEVERITY_BAR[s]} style={{ width: `${(counts[s] / total) * 100}%` }} />)}
            </span>
        </span>
    );
}

function Overflow({ items, max, render }: { items: string[]; max: number; render?: (item: string) => React.ReactNode }) {
    if (items.length === 0) return <span className="text-[11px] text-[#64748b]">—</span>;
    return (
        <span className="flex min-w-0 flex-wrap items-center gap-1" title={items.join(", ")}>
            {items.slice(0, max).map((item) => (
                <span key={item} className="min-w-0 truncate">{render ? render(item) : item}</span>
            ))}
            {items.length > max && <span className="text-[10px] text-[#94a3b8]">+{items.length - max}</span>}
        </span>
    );
}

const PortChip = ({ port }: { port: string }) => (
    <span className="rounded-md border border-[#a855f7]/45 bg-[#a855f7]/10 px-1.5 py-px text-[10px] font-semibold text-[#d8b4fe]">{port}</span>
);

export default function AssetsGrid({ scanId }: { scanId: string }) {
    const [assets, setAssets] = useState<DashboardAssetItem[]>([]);
    const [graph, setGraph] = useState<ScanGraphResponse | null>(null);
    const [findings, setFindings] = useState<DashboardFindingItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [typeFilter, setTypeFilter] = useState("all");
    const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({ key: "risk", dir: "desc" });
    const [view, setView] = useState<ViewMode>("list");
    const [openAssetId, setOpenAssetId] = useState<string | null>(null);
    const closeAsset = useCallback(() => setOpenAssetId(null), []);

    const searchParams = useSearchParams();
    const assetParam = searchParams.get("asset");
    const [handledAssetParam, setHandledAssetParam] = useState<string | null>(null);
    if (assetParam && assetParam !== handledAssetParam && assets.length > 0) {
        setHandledAssetParam(assetParam);
        const match = assets.find((a) => a.identifier === assetParam);
        if (match) setOpenAssetId(match.id);
    }

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        fetchAll((offset) => fetchScanAssets(scanId, { limit: PAGE_SIZE, offset }))
            .then((result) => { if (!cancelled) setAssets(result); })
            .catch((err: unknown) => { if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load assets"); })
            .finally(() => { if (!cancelled) setLoading(false); });
        fetchScanGraph(scanId).then((g) => { if (!cancelled) setGraph(g); }).catch(() => {});
        fetchAll((offset) => fetchScanFindings(scanId, { limit: PAGE_SIZE, offset }))
            .then((f) => { if (!cancelled) setFindings(f); }).catch(() => {});
        return () => { cancelled = true; };
    }, [scanId]);

    const insights = useMemo(() => buildInsights(graph, assets), [graph, assets]);
    const findingsByAsset = useMemo(() => {
        const map = new Map<string, DashboardFindingItem[]>();
        for (const f of findings) {
            if (!f.asset_identifier) continue;
            map.set(f.asset_identifier, [...(map.get(f.asset_identifier) ?? []), f]);
        }
        return map;
    }, [findings]);
    const countsFor = useCallback((asset: DashboardAssetItem) => severityCounts(findingsByAsset.get(asset.identifier) ?? []), [findingsByAsset]);
    const totalFor = (asset: DashboardAssetItem) => findingsByAsset.get(asset.identifier)?.length ?? asset.findings_count;

    const assetTypes = useMemo(() => Array.from(new Set(assets.map((a) => typeKey(a.asset_type)))), [assets]);
    const typeCounts = useMemo(() => {
        const counts: Record<string, number> = {};
        for (const a of assets) counts[typeKey(a.asset_type)] = (counts[typeKey(a.asset_type)] ?? 0) + 1;
        return counts;
    }, [assets]);

    const visibleAssets = useMemo(() => {
        const query = search.trim().toLowerCase();
        const filtered = assets
            .filter((a) => typeFilter === "all" || typeKey(a.asset_type) === typeFilter)
            .filter((a) => a.identifier.toLowerCase().includes(query));
        const value = (a: DashboardAssetItem): number | string => {
            switch (sort.key) {
                case "risk": return riskScore(countsFor(a)) * 1000 + (findingsByAsset.get(a.identifier)?.length ?? a.findings_count);
                case "findings": return findingsByAsset.get(a.identifier)?.length ?? a.findings_count;
                case "ports": return insights.get(a.id)?.ports.length ?? 0;
                case "type": return typeLabel(a.asset_type);
                case "name": return a.identifier;
            }
        };
        return [...filtered].sort((a, b) => {
            const va = value(a), vb = value(b);
            const cmp = typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb));
            return (sort.dir === "asc" ? cmp : -cmp) || a.identifier.localeCompare(b.identifier);
        });
    }, [assets, typeFilter, search, sort, countsFor, findingsByAsset, insights]);

    const rows = useMemo(() => {
        if (view === "list") return visibleAssets.map((asset) => ({ asset, nested: false, key: asset.id }));
        const byId = new Map(assets.map((a) => [a.id, a]));
        const visibleIds = new Set(visibleAssets.map((a) => a.id));
        const placed = new Set<string>();
        const out: { asset: DashboardAssetItem; nested: boolean; key: string }[] = [];
        for (const asset of visibleAssets.filter((a) => !isIpType(a.asset_type))) {
            out.push({ asset, nested: false, key: asset.id });
            placed.add(asset.id);
            for (const rel of insights.get(asset.id)?.related ?? []) {
                const ipAsset = rel.assetId ? byId.get(rel.assetId) : undefined;
                if (ipAsset && visibleIds.has(ipAsset.id)) {
                    out.push({ asset: ipAsset, nested: true, key: `${asset.id}>${ipAsset.id}` });
                    placed.add(ipAsset.id);
                }
            }
        }
        for (const asset of visibleAssets) if (!placed.has(asset.id)) out.push({ asset, nested: false, key: asset.id });
        return out;
    }, [view, visibleAssets, assets, insights]);

    function toggleSort(key: SortKey) {
        setSort((prev) => prev.key === key
            ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
            : { key, dir: key === "name" || key === "type" ? "asc" : "desc" });
    }
    const sortSelectValue = `${sort.key}:${sort.dir}`;
    const clearFilters = () => { setSearch(""); setTypeFilter("all"); };

    const subdomainCount = typeCounts.subdomain ?? 0;
    const ipCount = (typeCounts.ipv4 ?? 0) + (typeCounts.ipv6 ?? 0) + (typeCounts.ip ?? 0);
    const openAsset = openAssetId ? assets.find((a) => a.id === openAssetId) ?? null : null;

    const SortHeader = ({ label, sortKey }: { label: string; sortKey?: SortKey }) => sortKey ? (
        <button type="button" onClick={() => toggleSort(sortKey)}
            className={cn("flex items-center gap-1 text-left uppercase hover:text-foreground", sort.key === sortKey && "text-brand-cyan")}>
            {label}
            {sort.key === sortKey && <span aria-hidden="true">{sort.dir === "asc" ? "▲" : "▼"}</span>}
        </button>
    ) : <span>{label}</span>;

    return (
        <section className="min-w-0 pt-6" data-scan-id={scanId}>
            <div className="mb-5 grid grid-cols-[max-content_max-content_minmax(400px,1fr)] items-center gap-7 max-[1450px]:grid-cols-[auto_minmax(0,1fr)] max-[1100px]:flex max-[1100px]:flex-col max-[1100px]:items-stretch">
                <div>
                    <div className="flex items-center gap-2.5">
                        <h2 className="m-0 text-[25px] text-foreground">Assets</h2>
                        <span className="rounded-full bg-[#172338] px-2.5 py-1 text-[13px] text-[#dbeafe]">{assets.length}</span>
                    </div>
                    <p className="mt-2 text-[13px] text-muted-foreground">
                        {subdomainCount} subdomain{subdomainCount === 1 ? "" : "s"} · {ipCount} IP{ipCount === 1 ? "" : "s"}
                    </p>
                </div>

                <SummaryCard
                    title="Assets"
                    icon={Network}
                    accentClassName="bg-brand-cyan/10 text-brand-cyan"
                    value={assets.length}
                    items={assetTypes.map((type) => ({ label: typeLabel(type), value: typeCounts[type] }))}
                    colors={assetTypes.map((type) => TYPE_COLOR[type] ?? "#c084fc")}
                    keepBreakdownOnPhones
                    layout="side"
                    className="w-fit border"
                />

                <div className="grid w-full max-w-[760px] grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)] gap-2 justify-self-end max-[1450px]:col-span-full max-[1450px]:max-w-none max-[1450px]:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)] max-[1100px]:grid-cols-1 max-[720px]:grid-cols-[minmax(0,1fr)_auto]">
                    <label className="col-span-2 flex min-h-10 items-center gap-2.5 rounded-lg border border-brand-panel-border bg-brand-panel-deep px-3.5 max-[1450px]:col-span-1">
                        <span aria-hidden="true" className="text-muted-foreground">⌕</span>
                        <input
                            type="search"
                            placeholder="Search assets..."
                            aria-label="Search assets"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            autoCapitalize="off"
                            autoCorrect="off"
                            className="w-full border-0 bg-transparent text-foreground outline-none"
                        />
                    </label>
                    <FilterSheet activeCount={Number(typeFilter !== "all") + Number(sortSelectValue !== "risk:desc")}>
                        <select aria-label="Asset type" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className={selectClassName}>
                            <option value="all">Type: All</option>
                            {assetTypes.map((type) => <option key={type} value={type}>{typeLabel(type)}</option>)}
                        </select>
                        <select
                            aria-label="Sort assets"
                            value={sortSelectValue}
                            onChange={(e) => { const [key, dir] = e.target.value.split(":"); setSort({ key: key as SortKey, dir: dir as SortDir }); }}
                            className={selectClassName}
                        >
                            <option value="risk:desc">Sort: Riskiest first</option>
                            <option value="findings:desc">Sort: Most findings</option>
                            <option value="ports:desc">Sort: Most ports</option>
                            <option value="name:asc">Sort: Name A–Z</option>
                            <option value="type:asc">Sort: Type</option>
                        </select>
                    </FilterSheet>
                </div>
            </div>

            {error && <p className="mt-4 text-xs text-muted-foreground">{error}</p>}
            {loading && <p className="mt-4 text-xs text-muted-foreground">Loading assets...</p>}

            {!loading && !error && (
                <>
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                        <span className="text-[11px] text-[#94a3b8]">
                            Showing {visibleAssets.length} of {assets.length}
                        </span>
                        <span className="inline-flex overflow-hidden rounded-md border border-brand-panel-border">
                            {([["list", "List"], ["grouped", "Group IPs under subdomains"]] as const).map(([key, label]) => (
                                <button key={key} type="button" onClick={() => setView(key)} aria-pressed={view === key}
                                    className={cn("px-2.5 py-1 text-[11px] font-semibold", view === key ? "bg-brand-cyan/10 text-brand-cyan" : "text-[#94a3b8] hover:text-foreground")}>
                                    {label}
                                </button>
                            ))}
                        </span>
                    </div>

                    {visibleAssets.length === 0 ? (
                        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-brand-panel-border px-4 py-8 text-center">
                            <p className="m-0 text-sm text-muted-foreground">
                                {search.trim() ? <>No assets match &ldquo;{search.trim()}&rdquo;.</> : assets.length === 0 ? "No assets discovered yet." : "No assets match your filters."}
                            </p>
                            {(search.trim() || typeFilter !== "all") && (
                                <button type="button" onClick={clearFilters} className="text-xs font-semibold text-brand-cyan hover:underline">Clear filters</button>
                            )}
                        </div>
                    ) : (
                        <div className="min-w-0 overflow-x-auto border-t border-b border-brand-panel-border max-[720px]:overflow-visible max-[720px]:border-0">
                            <div className={cn(ROW_GRID, "min-w-[980px] border-b border-brand-panel-border px-4 py-2.5 text-[10px] font-semibold tracking-wide text-[#94a3b8] max-[720px]:hidden")}>
                                <SortHeader label="Asset" sortKey="name" />
                                <SortHeader label="Type" sortKey="type" />
                                <SortHeader label="Resolves to" />
                                <SortHeader label="Ports" sortKey="ports" />
                                <SortHeader label="Technology" />
                                <SortHeader label="Findings" sortKey="risk" />
                                <span />
                            </div>

                            <div className="max-[720px]:flex max-[720px]:flex-col max-[720px]:gap-2">
                                {rows.map(({ asset, nested, key: rowKey }) => {
                                    const info = insights.get(asset.id);
                                    const counts = countsFor(asset);
                                    const total = totalFor(asset);
                                    const related = info?.related.map((r) => r.label) ?? [];
                                    const ports = info?.ports.map((p) => p.port) ?? [];
                                    return (
                                        <button
                                            key={rowKey}
                                            type="button"
                                            onClick={() => setOpenAssetId(asset.id)}
                                            aria-haspopup="dialog"
                                            className={cn(
                                                "w-full border-0 border-b border-[#243047]/[0.76] bg-transparent text-left text-[#cbd5e1] transition-colors last:border-b-0 hover:bg-[#0d1928]",
                                                openAssetId === asset.id && "bg-[#0d1928] shadow-[inset_2px_0_#258cff]",
                                                "max-[720px]:rounded-lg max-[720px]:border max-[720px]:border-brand-panel-border max-[720px]:bg-brand-panel max-[720px]:last:border-b",
                                            )}
                                        >
                                            <span className={cn(ROW_GRID, "min-w-[980px] px-4 py-2.5 max-[720px]:hidden")}>
                                                <span className={cn("flex min-w-0 items-center gap-1.5", nested && "pl-5")}>
                                                    {nested && <span aria-hidden="true" className="text-[#475569]">↳</span>}
                                                    <strong className="truncate text-[13px] font-semibold text-foreground" title={asset.identifier}>{asset.identifier}</strong>
                                                </span>
                                                <TypeBadge type={asset.asset_type} />
                                                <span className="min-w-0 text-[11px] text-[#cbd5e1]"><Overflow items={related} max={2} /></span>
                                                <span className="min-w-0"><Overflow items={ports} max={3} render={(p) => <PortChip port={p} />} /></span>
                                                <span className="min-w-0 text-[11px] text-[#cbd5e1]"><Overflow items={info?.techs ?? []} max={1} /></span>
                                                <FindingsSummary counts={counts} total={total} />
                                                <ChevronRight className="size-4 text-[#64748b]" aria-hidden="true" />
                                            </span>

                                            <span className="hidden flex-col gap-1.5 p-3 max-[720px]:flex">
                                                <span className="flex items-start justify-between gap-2">
                                                    <strong className="min-w-0 text-sm font-semibold break-all text-foreground">{nested ? "↳ " : ""}{asset.identifier}</strong>
                                                    <TypeBadge type={asset.asset_type} />
                                                </span>
                                                {(related.length > 0 || ports.length > 0) && (
                                                    <span className="flex flex-wrap items-center gap-1.5 text-[11px] text-[#94a3b8]">
                                                        {related.length > 0 && <span className="truncate">→ {related.slice(0, 2).join(", ")}{related.length > 2 ? ` +${related.length - 2}` : ""}</span>}
                                                        {ports.slice(0, 3).map((p) => <PortChip key={p} port={p} />)}
                                                    </span>
                                                )}
                                                <span className="flex items-center justify-between gap-2">
                                                    <FindingsSummary counts={counts} total={total} />
                                                    <ChevronRight className="size-4 text-[#64748b]" aria-hidden="true" />
                                                </span>
                                            </span>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </>
            )}

            {openAsset && (
                <AssetDetails
                    asset={openAsset}
                    scanId={scanId}
                    info={insights.get(openAsset.id)}
                    findings={findingsByAsset.get(openAsset.identifier) ?? []}
                    onOpenAsset={setOpenAssetId}
                    onClose={closeAsset}
                />
            )}
        </section>
    );
}

export function AssetDetails({
    asset,
    scanId,
    info,
    findings,
    onOpenAsset,
    onClose,
}: {
    asset: DashboardAssetItem;
    scanId: string;
    info: AssetInsight | undefined;
    findings: DashboardFindingItem[];
    onOpenAsset: (assetId: string) => void;
    onClose: () => void;
}) {
    const counts = severityCounts(findings);
    const ip = isIpType(asset.asset_type);
    const categories = useMemo(() => {
        const groups = new Map<string, Map<string, { title: string; severity: Severity; ids: string[] }>>();
        for (const f of findings) {
            const category = f.cve_id ? "Known vulnerabilities (CVEs)" : CATEGORY_FOR_SOURCE[f.source] ?? "Other";
            const group = groups.get(category) ?? new Map();
            const key = `${f.severity}|${f.title}`;
            const entry = group.get(key) ?? { title: f.title, severity: f.severity.toLowerCase() as Severity, ids: [] };
            entry.ids.push(f.id);
            group.set(key, entry);
            groups.set(category, group);
        }
        return [...groups.entries()].map(([label, group]) => ({
            label,
            items: [...group.values()].sort((a, b) => SEVERITY_WEIGHT[b.severity] - SEVERITY_WEIGHT[a.severity] || a.title.localeCompare(b.title)),
            total: [...group.values()].reduce((n, i) => n + i.ids.length, 0),
        })).sort((a, b) => b.total - a.total);
    }, [findings]);

    const section = "m-0 mb-1.5 text-[10px] font-semibold tracking-wide text-[#94a3b8] uppercase";

    return (
        <SidePanelShell labelledBy="asset-details-title" onClose={onClose}>
            <header className="flex items-start justify-between gap-3 border-b border-brand-panel-border p-4">
                <div className="min-w-0">
                    <h2 id="asset-details-title" className="m-0 text-base leading-snug font-semibold break-all tracking-normal! text-foreground [font-family:inherit]!">
                        {asset.identifier}
                    </h2>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        <TypeBadge type={asset.asset_type} />
                        {SEVERITIES.filter((s) => counts[s] > 0).map((s) => (
                            <span key={s} className={cn("rounded-[5px] border px-1.5 py-px text-[10px] font-bold", SEVERITY_BADGE[s])}>{counts[s]} {capitalize(s)}</span>
                        ))}
                    </div>
                </div>
                <button type="button" onClick={onClose} aria-label="Close asset details"
                    className="grid size-8 shrink-0 place-items-center rounded-lg text-[#94a3b8] hover:bg-white/5 hover:text-foreground">
                    <X className="size-4" />
                </button>
            </header>

            <div className="min-h-0 overflow-y-auto overscroll-contain p-4">
                <div className="flex flex-col gap-4 rounded-lg border border-[#22324d] bg-[#0f1c30] p-4">
                    <section>
                        <h3 className={section}>{ip ? "Resolved from" : "Resolves to"}</h3>
                        {info && info.related.length > 0 ? (
                            <div className="flex flex-wrap gap-1.5">
                                {info.related.map((rel) => rel.assetId ? (
                                    <button key={rel.label} type="button" onClick={() => onOpenAsset(rel.assetId!)}
                                        className="rounded-md border border-[#26364e] bg-[#091523] px-2 py-0.5 text-[11px] text-brand-cyan hover:border-brand-cyan">
                                        {rel.label}
                                    </button>
                                ) : (
                                    <span key={rel.label} className="rounded-md border border-[#26364e] bg-[#091523] px-2 py-0.5 text-[11px] text-[#cbd5e1]">{rel.label}</span>
                                ))}
                            </div>
                        ) : <p className="m-0 text-[12px] text-[#64748b]">Nothing recorded.</p>}
                    </section>

                    <section>
                        <h3 className={section}>Open ports</h3>
                        {info && info.ports.length > 0 ? (
                            <ul className="m-0 grid list-none gap-1 p-0">
                                {info.ports.map((p) => (
                                    <li key={p.port} className="flex items-center gap-2 text-[12px] text-[#cbd5e1]">
                                        <PortChip port={p.port} />
                                        <span>{p.name}</span>
                                        {p.product && <span className="text-[#94a3b8]">· {p.product}</span>}
                                    </li>
                                ))}
                            </ul>
                        ) : <p className="m-0 text-[12px] text-[#64748b]">No open ports recorded.</p>}
                    </section>

                    <section>
                        <h3 className={section}>Technologies</h3>
                        {info && info.techs.length > 0 ? (
                            <div className="flex flex-wrap gap-1.5">
                                {info.techs.map((t) => (
                                    <span key={t} className="rounded-md border border-brand-success/40 bg-brand-success/10 px-2 py-0.5 text-[11px] text-brand-success">{t}</span>
                                ))}
                            </div>
                        ) : <p className="m-0 text-[12px] text-[#64748b]">None detected.</p>}
                    </section>

                    <section>
                        <h3 className={section}>Findings ({findings.length})</h3>
                        {categories.length === 0 ? (
                            <p className="m-0 text-[12px] text-[#64748b]">No findings on this asset.</p>
                        ) : (
                            <div className="flex flex-col gap-2.5">
                                {categories.map((cat) => (
                                    <div key={cat.label}>
                                        <p className="m-0 mb-1 text-[11px] font-semibold text-[#cbd5e1]">{cat.label} <span className="font-normal text-[#94a3b8]">· {cat.total}</span></p>
                                        <ul className="m-0 grid list-none gap-1 p-0">
                                            {cat.items.map((item) => (
                                                <li key={item.title + item.severity}>
                                                    <Link
                                                        href={`/phase2_scan/results/${scanId}/findings?finding=${encodeURIComponent(item.ids[0])}`}
                                                        className="flex items-center gap-2 rounded-md px-1.5 py-1 text-[12px] text-[#cbd5e1] no-underline hover:bg-white/5"
                                                    >
                                                        <span className={cn("size-1.5 shrink-0 rounded-full", SEVERITY_BAR[item.severity])} />
                                                        <span className="min-w-0 flex-1 truncate">{item.title}</span>
                                                        {item.ids.length > 1 && <span className="text-[10px] text-[#94a3b8]">×{item.ids.length}</span>}
                                                        <ChevronRight className="size-3.5 shrink-0 text-[#64748b]" />
                                                    </Link>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-[#22324d] pt-3">
                        <Link href={`/phase2_scan/results/${scanId}/findings?asset=${encodeURIComponent(asset.identifier)}`}
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-brand-cyan no-underline hover:underline">
                            View findings <ChevronRight className="size-3.5" />
                        </Link>
                        {info?.nodeId && (
                            <Link href={`/phase2_scan/results/${scanId}/graph?node=${encodeURIComponent(info.nodeId)}`}
                                className="inline-flex items-center gap-1 text-[11px] font-semibold text-brand-cyan no-underline hover:underline">
                                View on graph <ChevronRight className="size-3.5" />
                            </Link>
                        )}
                    </div>
                </div>
            </div>
        </SidePanelShell>
    );
}