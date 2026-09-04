"use client";
import {useEffect, useMemo, useState} from "react";
import Link from "next/link";
import {fetchScanAssets, type DashboardAssetItem} from "@/lib/scanService";
import {capitalize, cn} from "@/lib/utils";

type SortOption = "findings" | "name";
const selectClassName = "min-h-10 rounded-lg border border-brand-panel-border bg-brand-panel-deep px-3 text-foreground outline-none";

export default function AssetsGrid({scanId}: {scanId: string}) {
    const [assets, setAssets] = useState<DashboardAssetItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [typeFilter, setTypeFilter] = useState("all");
    const [sort, setSort] = useState<SortOption>("findings");
    const [selectedAsset, setSelectedAsset] = useState<DashboardAssetItem | null>(null);

    useEffect(() => {
        setLoading(true);
        fetchScanAssets(scanId, {limit: 100}).then((result) => {
            setAssets(result);
            setSelectedAsset(result[0] ?? null);
        })
        .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load assets"))
        .finally(() => setLoading(false));
    }, [scanId]);

    const assetTypes = useMemo(() => Array.from(new Set(assets.map((a) => a.asset_type))), [assets]);
    const typeCounts = useMemo(() => {
        const counts: Record<string, number> = {};
        for (const asset of assets) {
            counts[asset.asset_type] = (counts[asset.asset_type] ?? 0) + 1;
        }
        return counts;
    }, [assets]);

    const visibleAssets = useMemo(() => {
        const filtered = assets
            .filter((a) => typeFilter === "all" || a.asset_type === typeFilter)
            .filter((a) => a.identifier.toLowerCase().includes(search.trim().toLowerCase()));

        return [...filtered].sort((a,b) => sort === "findings" ? b.findings_count - a.findings_count : a.identifier.localeCompare(b.identifier));
    }, [assets, typeFilter, search, sort]);

    return(
        <section className="min-w-0 pt-6" data-scan-id={scanId}>
            <div className="mb-4.5 flex flex-col items-stretch gap-4 max-[1450px]:flex-col lg:flex-row lg:items-end lg:justify-between">
                <div>
                    <div className="flex items-center gap-2.5">
                        <h2 className="m-0 text-[25px] text-foreground"> Assets </h2>
                        <span className="rounded-full bg-[#172338] px-2.5 py-1 text-[13px] text-[#dbeafe]"> {assets.length} </span>
                    </div>
                    <div className="grid grid-cols-[minmax(220px,1fr)_minmax(120px,auto)_minmax(160px,auto)_minmax(170px,auto)] gap-3 max-[1450px]:grid-cols-[minmax(230px,1fr)_repeat(3,auto)] max-[1100px]:grid-cols-2 max-[720px]:grid-cols-1">
                        <label className="flex min-h-10 items-center gap-2.5 rounded-lg border border-brand-panel-border bg-brand-panel-deep px-3.5">
                            <span aria-hidden = "true" className="text-muted-foreground">⌕</span>
                            <input 
                                type = "search"
                                placeholder = "Search assets..."
                                aria-label = "Search assets"
                                value = {search}
                                onChange={(e) => setSearch(e.target.value)}
                                className = "w-full border-0 bg-transparent text-foreground outline-none"
                            />
                        </label>
                        <select
                            aria-label = "Asset type"
                            value = {typeFilter}
                            onChange={(e) => setTypeFilter(e.target.value)}
                            className = {selectClassName}
                        >
                            <option value = "all">Type: All</option>
                            {assetTypes.map((type) => (
                                <option key = {type} value={type}>
                                    {capitalize(type)}
                                </option>
                        ))}
                        </select>

                        <select 
                            value = {sort}
                            onChange = {(e) => setSort(e.target.value as SortOption)}
                            aria-label="Sort assets"
                            className={selectClassName}
                        >
                            <option value= "findings">Sort: Most Findings</option>
                            <option value= "name">Name: A to Z</option>
                        </select>
                    </div>
                </div>

                <div className = "mb-4.5 grid grid-cols-5 max-[1100px]:grid-cols-3 max-[1100px]:gap-y-2.5 max-[720px]:grid-cols-1">
                    {assetTypes.length === 0 ? (
                        <p className="mt-4 text-xs text-muted-foreground">No assets discovered yet.</p>
                    ): (
                        assetTypes.map((type) => (
                            <div
                                key = {type}
                                className="flex min-w-0 items-center gap-2.5 border-r border-brand-panel-border px-4.5 py-2 text-foreground first:pl-0 last:border-r-0 max-[720px]:border-r-0 max-[720px]:border-b max-[720px]:py-2.5"
                            >
                                <span className="grid gap-0.5">
                                    <small className="text-[11px] text-[#aeb9c8]"> {capitalize(type)} </small>
                                    <strong className="text-xl"> {typeCounts[type]} </strong>
                                </span>
                            </div>
                        ))
                    )}
                </div>
            </div>

                {error && <p className="mt-4 text-xs text-muted-foreground"> {error} </p>}
                {loading && <p className="mt-4 text-xs text-muted-foreground"> Loading assets... </p>}
                {!loading && !error && (
                    <div
                        className={cn("grid items-start gap-5", selectedAsset
                            ? "grid-cols-[minmax(0,1.35fr)_minmax(430px,0.95fr)] max-[1450px]:grid-cols-[minmax(0,1fr)_410px] max-[1100px]:grid-cols-1"
                            : "grid-cols-[minmax(0,1fr)]"
                )}
            >
                <div className="min-w-0">
                    <div className="min-w-0 border-t border-b border-brand-panel-border max-[720px]:overflow-x-auto">
                        <div className="grid min-h-[47px] grid-cols-[minmax(260px,1.8fr)_minmax(90px,0.65fr)_minmax(70px,0.45fr)_22px]
                                        items-center gap-3.5 border-b border-brand-panel-border px-4 text-[10px] text-muted-foreground uppercase max-[720px]:min-w-[670px]">
                                <span>Asset</span>  
                                <span>Type</span>  
                                <span>Findings</span>  
                                <span />                                  
                        </div>

                        <div>
                             {visibleAssets.length === 0 ? (
                                <p className="mt-4 text-xs text-muted-foreground">No assets match your filters.</p>
                             ) : (
                                visibleAssets.map((asset) => {
                                    const isSelected = selectedAsset?.id === asset.id;
                                    return (
                                        <button
                                            key={asset.id}
                                            type ="button"
                                            onClick={() => setSelectedAsset(asset)}
                                            className={cn("grid min-h-[72px] w-full grid-cols-[minmax(260px,1.8fr)_minmax(90px,0.65fr)_minmax(70px,0.45fr)_22px] items-center gap-3.5 border-0 border-b border-[#243047]/[0.76] bg-transparent px-4 text-left text-[#cbd5e1] last:border-b-0 hover:bg-[#0d1928] max-[720px]:min-w-[670px]",
                                            isSelected && "bg-[#0d1928] shadow-[inset_2px_0_#258cff]"
                                    )}
                                >
                                    <span className="flex min-w-0 items-center gap-3">
                                        <strong className="overflow-hidden text-[13px] text-foreground text-ellipsis whitespace-nowrap">
                                            {asset.identifier}
                                        </strong>
                                    </span>

                                    <span className="text-[11px] text-[#aeb9c8]">{capitalize(asset.asset_type)}</span>
                                    <strong className="text-base font-medium">{asset.findings_count}</strong>
                                    <span className="text-[21px] text-[#cbd5e1]" aria-hidden ="true">{`>`}</span>
                                </button>
                             );
                            })
                        )}
                        </div>
                    </div>
                </div>

                {selectedAsset && (
                    <aside className="min-w-0 overflow-hidden rounded-[9px] border border-brand-panel-border bg-[#0b1625] max-[1100px]:static max-[1100px]:max-h-none lg:sticky lg:top-5 lg:max-h-[calc(100vh-40px)]">
                        <header className="flex items-start justify-between gap-4 border-b border-brand-panel-border p-4.5 max-[720px]:flex-col">
                            <div className="flex min-w-0 items-start gap-3">
                                <div>
                                    <h2 className="mt-px mb-1.5 text-lg break-words text-foreground"> {selectedAsset.identifier} </h2>
                                    <p className="m-0 flex flex-wrap gap-1.5 text-[10px] text-muted-foreground">
                                        {capitalize(selectedAsset.asset_type)}
                                        <span>•</span>
                                        <strong className="font-medium text-brand-alert"> {selectedAsset.findings_count} findings </strong>
                                    </p>
                                </div>
                            </div>

                            <div className="flex shrink-0 items-center gap-3 max-[720px]:w-full max-[720px]:justify-between">
                                <button
                                    type = "button"
                                    aria-label="close asset details"
                                    onClick={()=> setSelectedAsset(null)}
                                    className="border-0 bg-transparent text-2xl text-muted-foreground hover:text-white">x</button>
                            </div>
                        </header>

                        <div className="max-h-[calc(100vh-135px)] overflow-y-auto p-4 max-[1100px]:max-h-none">
                            <section className="border-b border-brand-panel-border pb-4">
                                <h3 className="mt-0 mb-4 text-[13px] text-foreground">Overview</h3>
                                <div className="grid grid-cols-2 max-[720px]:grid-cols-1">
                                    <dl className="m-0 grid gap-3.5 border-r border-brand-panel-border pr-4 max-[720px]:border-r-0 max-[720px]:border-b max-[720px]:pr-0 max-[720px]:pb-3.5">
                                        <div className="grid gap-1">
                                            <dt className="text-[10px] text-muted-foreground">Type</dt>
                                            <dd className="m-0 text-[11px] text-foreground"> {capitalize(selectedAsset.asset_type)}</dd>
                                        </div>
                                        <div className="grid gap-1">
                                            <dt className="text-[10px] text-muted-foreground">Open Findings</dt>
                                            <dd className="m-0 text-[11px] text-foreground"> {selectedAsset.findings_count} </dd>
                                        </div>
                                    </dl>
                                </div>
                            </section>

                            <Link
                                href={`/phase2_scan/results/${scanId}/findings?asset=${encodeURIComponent(selectedAsset.identifier)}`}
                                className="relative mt-3.5 grid gap-1 rounded-lg border border-[#26364e] bg-[#0c1828] px-3.5 py-3 pr-10 text-center no-underline hover:border-[#155da1] hover:bg-[#102036]"
                                >
                                    <strong className="text-[10px] text-[#70b9ff]">View findings in the Findings tab</strong>
                            </Link>
                        </div>
                    </aside>
                )}
                </div>
                )}
        </section>
    );
}