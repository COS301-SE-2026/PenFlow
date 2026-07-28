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
                    
                </div>
            </div>
        </section>
    )
}