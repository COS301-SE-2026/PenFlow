"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {FolderKey, Globe, Lock, Mail, Network, Server, Terminal, type LucideIcon,} from "lucide-react";
import {cn} from "@/lib/utils";

import {fetchScanServices, type ServiceListItem, type ServiceSummaryCounts} from "@/lib/scanService";
type ProtocolFilter = "ALL" | "TCP" | "UDP";
type SortOption = "recent" | "port";

const LIMIT = 15;
const selectClassName = "min-h-10 rounded-lg border border-brand-panel-border bg-brand-panel-deep px-3 text-foreground outline-none";

const riskClassName: Record<string, string> = {

    critical: "border-[#991b1b] text-[#ef4444] bg-[#991b1b]/[0.1]",
    high: "border-brand-orange/70 text-brand-orange bg-brand-orange/10",
    medium: "border-brand-yellow/70 text-brand-yellow bg-brand-yellow/10",
    low: "border-[#1e40af] text-[#60a5fa] bg-[#1e40af]/10",
};

const SERVICE_ICONS: Record<string, LucideIcon> = {
    https: Lock,
    http: Globe,
    "http-alt": Globe,
    ssh: Terminal,
    smtp: Mail,
    smtps: Mail,
    imaps: Mail,
    dns: Network,
    ftp: FolderKey,
};

function serviceIcon(serviceName: string): LucideIcon {
    return SERVICE_ICONS[serviceName.toLowerCase()] ?? Server;
}

function formatTimestamp(iso:string):string {
    return new Date(iso).toLocaleString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function RiskBadge({riskLevel}: {riskLevel: string}) {
    return (
        <span
            className={cn(
                "w-fit rounded-[5px] border px-2 py-1 text-[9px] font-semibold uppercase",
                riskClassName[riskLevel.toLowerCase()] ?? "border-brand-panel-border text-muted-foreground"
            )}
        >
            {riskLevel}
        </span>
    );
}

export default function ServicesView({scanId}:{scanId:string}) {
    const [services, setServices] = useState<ServiceListItem[]>([]);
    const [counts, setCounts] = useState<ServiceSummaryCounts | null>(null);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [search, setSearch] = useState("");
    const [debouncedSearch, setDebouncedSearch] = useState("");
    const [protocolFilter, setProtocolFilter] = useState<ProtocolFilter>("ALL");
    const [sortBy, setSortBy] = useState<SortOption>("recent");
    const [selectedService, setSelectedService] = useState<ServiceListItem | null>(null);

    const requestIdRef = useRef(0);

    useEffect(() => {
        const handle = setTimeout(() => setDebouncedSearch(search.trim()), 350);
        return() => clearTimeout(handle);
    }, [search]);

    const loadServices = useCallback(
    async (params: {offset: number; append: boolean}) => {
        const requestId = ++requestIdRef.current;
        setLoading(true);
        setError(null);
        try {
            const result = await fetchScanServices(scanId, {
                protocol: protocolFilter === "ALL" ? undefined: protocolFilter,
                search: debouncedSearch || undefined,
                sort_by: sortBy,
                limit: LIMIT,
                offset: params.offset,
            });
            if(requestIdRef.current !== requestId) return;

            setServices((prev) => (params.append ? [...prev, ...result.items]: result.items));
            setCounts(result.counts);
            setTotal(result.total);
            if(!params.append) {
                setSelectedService(result.items[0] ?? null);
            }
        }catch (err) {
            if (requestIdRef.current !== requestId) return;
            setError(err instanceof Error ? err.message : "Failed to load services");
        } finally {
            if (requestIdRef.current === requestId) setLoading(false);
        }
    }, [scanId, protocolFilter, debouncedSearch, sortBy]
);

useEffect(() => {
    void loadServices ({offset:0, append: false});
}, [loadServices]);

function handleLoadMore() {
    if(loading || services.length >= total) return;
    void loadServices ({offset: services.length, append: true});
}

const hasMore = services.length < total;

return (
    <section className="min-w-0 pt-6" data-scan-id = {scanId}>
        <div className="mb-4.5 flex flex-col items-stretch gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
                <div className="flex items-center gap-2.5">
                    <h2 className="m-0 text-[25px] text-foreground">
                        Services
                    </h2>
                    <span className="rounded-full bg-[#172338] px-2.5 py-1 text-[13px] text-[#dbeafe]">{total}</span>
                </div>
            </div>

            <div className="grid grid-cols-[minmax(220px,1fr)_minmax(120px,auto)_minmax(160px,auto)] gap-3 max-[1100px]:grid-cols-2 max-[720px]:grid-cols-1">
            <label className="flex min-h-10 items-center gap-2.5 rounded-lg border border-brand-panel-border bg-brand-panel-deep px-3.5">
                <span aria-hidden="true" className="text-muted-foreground">⌕</span>
                <input
                    type = "search"
                    placeholder = "Search services..."
                    aria-label = "Search services"
                    value = {search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full border-0 bg-transparent text-foreground outline-none"    
                />
            </label>
            <select
                value = {protocolFilter}
                onChange = {(e) => setProtocolFilter(e.target.value as ProtocolFilter)}
                aria-label = "Protocol"
                className= {selectClassName}
            >
                <option value="ALL">Protocol: ALL</option>
                <option value="TCP">TCP</option>
                <option value="UDP">UDP</option>
            </select>

            <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                aria-label = "Sort services"
                className={selectClassName}
            >
                <option value="recent">Sort: Most Recent</option>
                <option value="port">Sort: Port</option>
            </select>
            </div>
        </div>

        <div className="mb-4.5 grid grid-cols-5 max-[1100px]:grid-cols-3 max-[1100px]:gap-y-2.5 max-[720px]:grid-cols-1">
    <div className="flex min-w-0 items-center gap-2.5 border-r border-brand-panel-border px-4.5 py-2 text-foreground first:pl-0 last:border-r-0 max-[720px]:border-r-0 max-[720px]:border-b max-[720px]:py-2.5">
        <span className="grid size-9 shrink-0 place-items-center rounded-full bg-brand-cyan/10 text-brand-cyan">
            <Globe className="size-4" />
        </span>
        <span className="grid gap-0.5">
            <small className="text-[11px] text-[#aeb9c8]">All Services</small>
            <strong className="text-xl">{counts?.total ?? 0}</strong>
        </span>
    </div>
    <div className="flex min-w-0 items-center gap-2.5 border-r border-brand-panel-border px-4.5 py-2 text-foreground last:border-r-0 max-[720px]:border-r-0 max-[720px]:border-b max-[720px]:py-2.5">
        <span className="grid size-9 shrink-0 place-items-center rounded-full bg-[#3b82f6]/10 text-[10px] font-bold text-[#3b82f6]">
            TCP
        </span>
        <span className="grid gap-0.5">
            <small className="text-[11px] text-[#aeb9c8]">TCP</small>
            <strong className="text-xl">{counts?.tcp ?? 0}</strong>
        </span>
    </div>
    <div className="flex min-w-0 items-center gap-2.5 border-r border-brand-panel-border px-4.5 py-2 text-foreground last:border-r-0 max-[720px]:border-r-0 max-[720px]:border-b max-[720px]:py-2.5">
        <span className="grid size-9 shrink-0 place-items-center rounded-full bg-[#a855f7]/10 text-[10px] font-bold text-[#a855f7]">
            UDP
        </span>
        <span className="grid gap-0.5">
            <small className="text-[11px] text-[#aeb9c8]">UDP</small>
            <strong className="text-xl">{counts?.udp ?? 0}</strong>
        </span>
    </div>
    <div className="flex min-w-0 items-center gap-2.5 border-r border-brand-panel-border px-4.5 py-2 text-foreground last:border-r-0 max-[720px]:border-r-0 max-[720px]:border-b max-[720px]:py-2.5">
        <span className="size-2.5 shrink-0 rounded-full bg-brand-success" />
        <span className="grid gap-0.5">
            <small className="text-[11px] text-[#aeb9c8]">Open</small>
            <strong className="text-xl">{counts?.open ?? 0}</strong>
        </span>
    </div>
    <div className="flex min-w-0 items-center gap-2.5 px-4.5 py-2 text-foreground max-[720px]:py-2.5">
        <span className="size-2.5 shrink-0 rounded-full bg-brand-yellow" />
        <span className="grid gap-0.5">
            <small className="text-[11px] text-[#aeb9c8]">Filtered</small>
            <strong className="text-xl">{counts?.filtered ?? 0}</strong>
        </span>
    </div>
</div>

{error && <p className="mt-4 text-xs text-muted-foreground"> {error} </p>}
<div   
    className={cn("grid items-start gap-5", selectedService ? "grid-cols-[minmax(0,1.35fr)_minmax(430px,0.95fr)] max-[1450px]:grid-cols-[minmax(0,1fr)_410px] max-[1100px]:grid-cols-1"
        : "grid-cols-[minmax(0,1fr)]"
)}
>
    <div className="min-w-0">
        <div className="min-w-0 border-t border-b border-brand-panel-border max-[720px]:overflow-x-auto">
            <div className="grid min-h-[47px] grid-cols-[minmax(220px,1.6fr)_minmax(70px,0.5fr)_minmax(60px,0.4fr)] items-center gap-3.5 border-b border-brand-panel-border px-4 text-[10px] text-muted-foreground uppercase max-[720px]:min-w-[720px]">
                <span>Service / Port</span>
                <span>Protocol</span>
                <span>State</span>
                <span>Assets</span>
                <span>Risk</span>
                <span>Detected On</span>
            </div>

            <div>
                {!loading && services.length === 0 ? (
                    <p className="mt-4 text-xs text-muted-foreground">No services match your filters.</p>
                ): (
                    services.map((service) => {
                        const isSelected = selectedService?.id === service.id;
                        const Icon = serviceIcon(service.service_name);
                        const isOpen = service.state.toLowerCase() === "open";

                        return (
                            <button
                                key = {service.id}
                                type = "button"
                                onClick={() => setSelectedService(service)}
                                className={cn(
                                    "grid min-h-[64px] w-full grid-cols-[minmax(220px,1.6fr)_minmax(70px,0.5fr)_minmax(70px,0.5fr)_minmax(60px,0.4fr)_minmax(70px,0.5fr)_minmax(120px,0.7fr)] items-center gap-3.5 border-0 border-b border-[#243047]/[0.76] bg-transparent px-4 text-left text-[#cbd5e1] last:border-b-0 hover:bg-[#0d1928] max-[720px]:min-w-[720px]",
                                    isSelected && "bg-[#0d1928] shadow-[inset_2px_0_#258cff]"
                        )}
                            >
                                <span className="flex min-w-0 items-center gap-2.5">
                                    <span className="grid size-8 shrink-0 place-items-center rounded-full bg-brand-panel-deep text-muted-foreground">
                                        <Icon className="size-4" />
                                    </span>
                                    <span className="grid min-w-0 gap-0.5">
                                        <strong className="overflow-hidden text-[13px] text-ellipsis whitespace-nowrap text-foreground">
                                            {service.service_name}
                                        </strong>
                                        <small className="text-[10px] text-muted-foreground">
                                            {service.port}/{service.protocol.toLowerCase()}
                                        </small>
                                    </span>
                                </span>

                                <span className="text-[11px] text-[#aeb9c8]"> {service.protocol}</span>
                                <span className="flex items-center gap-1.5 text-[11px] text-[#aeb9c8]">
                                    <span className={cn("size-1.5 rounded-full", isOpen ? "bg-brand-success" : "bg-brand-yellow")}/>
                                    {service.state}
                                </span>

                                <span className="text-[11px] text-[#aeb9c8]">{service.asset_count}</span>
                                <RiskBadge riskLevel={service.risk_level}/>
                                <span className="text-[11px] text-[#aeb9c8]">
                                    {formatTimestamp(service.created_at)}
                                </span>
                            </button>
                        );
                    })
                )}
            </div>
        </div>

        {hasMore && (
            <div className="flex justify-center py-4">
                <button
                    type = "button"
                    onClick= {handleLoadMore}
                    disabled = {loading}
                    className="rounded-lg border border-brand-panel-border bg-brand-panel-deep px-4 py-2 text-xs text-foreground hover:bg-brand-panel"
                >
                    {loading ? "Loading..." : "Load more services"}
                </button>
            </div>
        )}
    </div>

    {selectedService && (
        <aside className="min-w-0 overflow-hidden rounded-[9px] border border-brand-panel-border bg-[#0b1625] max-[1100px]:static max-[1100px]:max-h-none lg:sticky lg:top-5 lg:max-h-[calc(100vh-40px)]">
            <header className="flex items-start justify-between gap-4 border-b border-brand-panel-border p-4.5">
                <div className="flex min-w-0 items-start gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-full bg-brand-panel-deep text-muted-foreground">
                        {(() => {
                            const Icon = serviceIcon(selectedService.service_name);
                            return <Icon className="size-5"/>;
                        })()}
                    </span>
                    <div>
                        <h2 className="mt-px mb-1.5 text-lg break-words text-foreground">
                            {selectedService.service_name}
                        </h2>
                        <p className="m-0 text-[11px] text-muted-foreground">
                            {selectedService.port}/{selectedService.protocol.toLowerCase()}
                        </p>
                    </div>
                </div>

                <div className="flex shrink-0 items-center gap-3">
                    <RiskBadge riskLevel= {selectedService.risk_level}/>
                        <button
                            type = "button"
                            aria-label = "Close service details"
                            onClick= {() => setSelectedService(null)}
                            className="border-0 bg-transparent text-2xl text-muted-foreground hover:text-white"
                        >
                            ×
                        </button>
                </div>
            </header>

            <div className="max-h-[calc(100vh-135px)] overflow-y-auto p-4 max-[1100px]:max-h-none">
                <section>
                    <h3 className="mt-0 mb-4 text-[13px] text-foreground">
                        Overview
                    </h3>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-3.5">
                        <div className="grid gap-1">
                            <dt className="text-[10px] text-muted-foreground">Protocol</dt>
                            <dd className="m-0 text-[11px] text-foreground">{selectedService.protocol}</dd>
                        </div>
                        <div className="grid gap-1">
                            <dt className="text-[10px] text-muted-foreground">Port</dt>
                            <dd className="m-0 text-[11px] text-foreground">{selectedService.port}</dd>
                        </div>
                    

                    
                        <div className="grid gap-1">
                            <dt className="text-[10px] text-muted-foreground">State</dt>
                            <dd className="m-0 text-[11px] text-foreground">{selectedService.state}</dd>
                        </div>
                    

                    
                        <div className="grid gap-1">
                            <dt className="text-[10px] text-muted-foreground">Risk</dt>
                            <dd className="m-0 text-[11px] text-foreground">{selectedService.risk_level}</dd>
                        </div>
                   

                    {selectedService.product && (
                        <div className="grid gap-1">
                            <dt className="text-[10px] text-muted-foreground">Product</dt>
                            <dd className="m-0 text-[11px] text-foreground">{selectedService.product}</dd>
                        </div>
                    )}

                    {selectedService.version && (
                        <div className="grid gap-1">
                            <dt className="text-[10px] text-muted-foreground">Version</dt>
                            <dd className="m-0 text-[11px] text-foreground">{selectedService.version}</dd>
                        </div>
                    )}

                        <div className="grid gap-1">
                            <dt className="text-[10px] text-muted-foreground">Assets</dt>
                            <dd className="m-0 text-[11px] text-foreground">{selectedService.asset_count}</dd>
                        </div>

                        <div className="grid gap-1">
                            <dt className="text-[10px] text-muted-foreground">Detected</dt>
                            <dd className="m-0 text-[11px] text-foreground">{formatTimestamp(selectedService.created_at)}</dd>
                        </div>
                    </div>
                </section>

                {selectedService.banner && (
                    <section className="mt-3.5 border-t border-brand-panel-border pt-3.5">
                        <h3 className="mt-0 mb-2 text-[13px] text-foreground">
                            Banner
                        </h3>
                        <p className="m-0 [overflow-wrap:anywhere] text-[11px] leading-[1.6] text-[#abb7c7]">
                            {selectedService.banner}
                        </p>
                    </section>
                )}
            </div>
        </aside>
    )}
</div>
</section>
);}

