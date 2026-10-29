"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronRight, Info, Lock, Server, X } from "lucide-react";

import {
    fetchScanFindings,
    fetchScanGraph,
    fetchScanServices,
    type DashboardFindingItem,
    type GraphNode,
    type ScanGraphResponse,
    type ServiceListItem,
} from "@/lib/scanService";
import { capitalize, cn } from "@/lib/utils";
import { FilterSheet } from "@/shared/components/DetailSheet";
import SidePanelShell from "@/shared/components/SidePanelShell";
import { formatDateTime } from "@/lib/engagementFormat";
import { SummaryCard } from "./SummaryCard";

type Severity = "critical" | "high" | "medium" | "low" | "info";
type SortKey = "risk" | "port" | "service" | "host" | "findings";
type SortDir = "asc" | "desc";
type ViewMode = "list" | "port" | "host";

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"];
const SEVERITY_WEIGHT: Record<Severity, number> = { critical: 40, high: 20, medium: 8, low: 3, info: 1 };
const SEVERITY_TEXT: Record<Severity, string> = {
    critical: "text-[#ef4444]", high: "text-[#f97316]", medium: "text-[#facc15]", low: "text-[#60a5fa]", info: "text-[#94a3b8]",
};
const SEVERITY_BAR: Record<Severity, string> = {
    critical: "bg-[#ef4444]", high: "bg-[#f97316]", medium: "bg-[#facc15]", low: "bg-[#3b82f6]", info: "bg-[#64748b]",
};
const SEVERITY_BADGE: Record<Severity, string> = {
    critical: "border-[#991b1b] text-[#ef4444] bg-[#991b1b]/[0.08]",
    high: "border-[#a34908] text-[#f97316] bg-[#a34908]/[0.08]",
    medium: "border-[#8a6a00] text-[#facc15] bg-[#8a6a00]/[0.08]",
    low: "border-[#18549a] text-[#60a5fa] bg-[#18549a]/[0.08]",
    info: "border-[#334155] text-[#94a3b8] bg-[#334155]/[0.08]",
};
const CHART_COLORS = ["#2bd8f5", "#a855f7", "#60a5fa", "#4ade80", "#facc15", "#f97316", "#94a3b8"];

const CATEGORY_FOR_SOURCE: Record<string, string> = {
    http_security: "HTTP security headers",
    https_security: "HTTP security headers",
    tls: "TLS & certificates",
    cve: "Known vulnerabilities (CVEs)",
    hibp: "Data breaches",
    dns: "DNS & email",
};

const PORT_GROUPS: { key: string; label: string; ports: number[] }[] = [
    { key: "web", label: "Web", ports: [80, 443, 8000, 8008, 8080, 8443, 8888] },
    { key: "mail", label: "Mail", ports: [25, 110, 143, 465, 587, 993, 995] },
    { key: "remote", label: "Remote access", ports: [22, 23, 3389, 5900] },
    { key: "db", label: "Databases", ports: [1433, 1521, 3306, 5432, 6379, 27017] },
];

const PAGE_SIZE = 100;
const selectClassName = "min-h-10 w-full rounded-lg border border-brand-panel-border bg-brand-panel-deep px-3 text-foreground outline-none";
const ROW_GRID = "grid grid-cols-[104px_minmax(150px,1fr)_minmax(200px,1.3fr)_minmax(140px,1fr)_40px_minmax(160px,auto)_16px] items-center gap-x-4";
const TCPWRAPPED_HELP = "The port is open, but the service closed the connection before identifying itself — often a firewall, proxy or load balancer in front of it.";

async function fetchAllServices(scanId: string): Promise<ServiceListItem[]> {
    const all: ServiceListItem[] = [];
    for (let offset = 0; offset < 5000; offset += PAGE_SIZE) {
        const page = await fetchScanServices(scanId, { sort_by: "port", limit: PAGE_SIZE, offset });
        all.push(...page.items);
        if (page.items.length < PAGE_SIZE || all.length >= page.total) break;
    }
    return all;
}
async function fetchAllFindings(scanId: string): Promise<DashboardFindingItem[]> {
    const all: DashboardFindingItem[] = [];
    for (let offset = 0; offset < 5000; offset += PAGE_SIZE) {
        const page = await fetchScanFindings(scanId, { limit: PAGE_SIZE, offset });
        all.push(...page);
        if (page.length < PAGE_SIZE) break;
    }
    return all;
}

const isUnknownService = (name: string) => !name || name.toLowerCase() === "tcpwrapped" || name.toLowerCase() === "unknown";
const serviceLabel = (s: ServiceListItem) => (isUnknownService(s.service_name) ? "Unknown" : s.service_name.toUpperCase());
const portLabel = (s: ServiceListItem) => `:${s.port}/${s.protocol.toLowerCase()}`;
const productLabel = (s: ServiceListItem) => [s.product, s.version].filter(Boolean).join(" ");

interface ServiceInsight {
    nodeId: string | null;
    hostnames: string[];
    tls: boolean;
    techs: string[];
    findings: DashboardFindingItem[];
}

function buildInsights(
    services: ServiceListItem[],
    graph: ScanGraphResponse | null,
    findings: DashboardFindingItem[],
): Map<string, ServiceInsight> {
    const result = new Map<string, ServiceInsight>();
    const nodesById = new Map((graph?.nodes ?? []).map((n) => [n.id, n]));
    const edges = graph?.edges ?? [];
    const findingsByAsset = new Map<string, DashboardFindingItem[]>();
    for (const f of findings) if (f.asset_identifier) findingsByAsset.set(f.asset_identifier, [...(findingsByAsset.get(f.asset_identifier) ?? []), f]);
    const findingById = new Map(findings.map((f) => [f.id, f]));

    for (const svc of services) {
        const nodeId = `service:${svc.id}`;
        const node = nodesById.get(nodeId);
        const hostNodeId = edges.find((e) => e.target === nodeId && e.type === "EXPOSES")?.source;
        const hostnames = hostNodeId
            ? edges.filter((e) => e.target === hostNodeId && e.type === "RESOLVES_TO")
                .map((e) => nodesById.get(e.source)?.label)
                .filter((l): l is string => Boolean(l))
            : [];
        const tls = node?.metadata.tls_enabled === true || svc.port === 443 || svc.service_name.toLowerCase() === "https";
        const techs = [...new Set(edges.filter((e) => e.source === nodeId && e.type === "RUNS")
            .map((e) => nodesById.get(e.target)?.label).filter((l): l is string => Boolean(l)))];

        const related = new Map<string, DashboardFindingItem>();
        edges.filter((e) => e.source === nodeId && e.type === "AFFECTED_BY").forEach((e) => {
            const f = nodesById.get(e.target) as GraphNode | undefined;
            const item = f?.entity_id ? findingById.get(f.entity_id) : undefined;
            if (item) related.set(item.id, item);
        });
        for (const owner of [svc.host, ...hostnames]) {
            for (const f of findingsByAsset.get(owner) ?? []) {
                const matches = (f.source === "http_security" && svc.port === 80)
                    || (f.source === "https_security" && svc.port === 443)
                    || (f.source === "tls" && tls)
                    || (f.cve_id && techs.some((t) => f.title.toLowerCase().includes(t.split(/\s+/)[0].toLowerCase())));
                if (matches) related.set(f.id, f);
            }
        }
        result.set(svc.id, { nodeId: node ? nodeId : null, hostnames, tls, techs, findings: [...related.values()] });
    }
    return result;
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

function PortChip({ svc }: { svc: ServiceListItem }) {
    const filtered = svc.state.toLowerCase() !== "open";
    const udp = svc.protocol.toLowerCase() === "udp";
    return (
        <span className="flex flex-col items-start gap-1">
            <span className="rounded-md border border-[#a855f7]/45 bg-[#a855f7]/10 px-1.5 py-px font-mono text-[11px] font-semibold text-[#d8b4fe]">{portLabel(svc)}</span>
            {(filtered || udp) && (
                <span className="flex gap-1">
                    {udp && <span className="rounded-[4px] border border-[#a855f7]/50 px-1 text-[9px] font-bold text-[#c084fc] uppercase">UDP</span>}
                    {filtered && <span className="rounded-[4px] border border-brand-yellow/60 px-1 text-[9px] font-bold text-brand-yellow uppercase">{svc.state}</span>}
                </span>
            )}
        </span>
    );
}

function ServiceName({ svc }: { svc: ServiceListItem }) {
    if (!isUnknownService(svc.service_name)) return <span className="font-semibold text-foreground">{serviceLabel(svc)}</span>;
    return (
        <span className="inline-flex items-center gap-1 font-semibold text-foreground" title={TCPWRAPPED_HELP}>
            Unknown <span className="font-normal text-[#94a3b8]">({svc.service_name || "unidentified"})</span>
            <Info className="size-3.5 text-[#94a3b8]" aria-label={TCPWRAPPED_HELP} />
        </span>
    );
}

function FindingsSummary({ findings }: { findings: DashboardFindingItem[] }) {
    const counts = severityCounts(findings);
    const present = SEVERITIES.filter((s) => counts[s] > 0);
    if (present.length === 0) return <span className="text-[11px] text-[#64748b]">No findings</span>;
    return (
        <span className="flex min-w-0 flex-col gap-1">
            <span className="flex flex-wrap gap-x-2 text-[11px] font-semibold">
                {present.map((s) => <span key={s} className={SEVERITY_TEXT[s]}>{counts[s]} {capitalize(s)}</span>)}
            </span>
            <span className="flex h-1 w-full max-w-[140px] overflow-hidden rounded-full bg-white/5">
                {present.map((s) => <span key={s} className={SEVERITY_BAR[s]} style={{ width: `${(counts[s] / findings.length) * 100}%` }} />)}
            </span>
        </span>
    );
}

export default function ServicesView({ scanId }: { scanId: string }) {
    const [services, setServices] = useState<ServiceListItem[]>([]);
    const [graph, setGraph] = useState<ScanGraphResponse | null>(null);
    const [findings, setFindings] = useState<DashboardFindingItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [protocolFilter, setProtocolFilter] = useState("all");
    const [portGroup, setPortGroup] = useState("all");
    const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({ key: "risk", dir: "desc" });
    const [view, setView] = useState<ViewMode>("list");
    const [openServiceId, setOpenServiceId] = useState<string | null>(null);
    const closeService = useCallback(() => setOpenServiceId(null), []);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        fetchAllServices(scanId)
            .then((result) => { if (!cancelled) setServices(result); })
            .catch((err: unknown) => { if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load services"); })
            .finally(() => { if (!cancelled) setLoading(false); });
        fetchScanGraph(scanId).then((g) => { if (!cancelled) setGraph(g); }).catch(() => {});
        fetchAllFindings(scanId).then((f) => { if (!cancelled) setFindings(f); }).catch(() => {});
        return () => { cancelled = true; };
    }, [scanId]);

    const insights = useMemo(() => buildInsights(services, graph, findings), [services, graph, findings]);
    const findingsFor = useCallback((svc: ServiceListItem) => insights.get(svc.id)?.findings ?? [], [insights]);
    const hostLabel = useCallback((svc: ServiceListItem) => {
        const names = insights.get(svc.id)?.hostnames ?? [];
        return names.length > 0 ? `${svc.host} · ${names.join(", ")}` : svc.host;
    }, [insights]);

    const protocols = useMemo(() => [...new Set(services.map((s) => s.protocol.toUpperCase()))], [services]);
    const allOpen = services.length > 0 && services.every((s) => s.state.toLowerCase() === "open");
    const hostCount = useMemo(() => new Set(services.map((s) => s.host)).size, [services]);
    const portGroupCounts = useMemo(() => Object.fromEntries(
        PORT_GROUPS.map((g) => [g.key, services.filter((s) => g.ports.includes(s.port)).length]),
    ), [services]);

    const typeCounts = useMemo(() => {
        const counts = new Map<string, number>();
        for (const s of services) counts.set(serviceLabel(s), (counts.get(serviceLabel(s)) ?? 0) + 1);
        return [...counts.entries()].sort((a, b) => b[1] - a[1]);
    }, [services]);

    const visibleServices = useMemo(() => {
        const query = search.trim().toLowerCase();
        const group = PORT_GROUPS.find((g) => g.key === portGroup);
        const filtered = services
            .filter((s) => protocolFilter === "all" || s.protocol.toUpperCase() === protocolFilter)
            .filter((s) => !group || group.ports.includes(s.port))
            .filter((s) => !query || [String(s.port), s.service_name, s.host, productLabel(s), ...(insights.get(s.id)?.hostnames ?? [])]
                .some((v) => v.toLowerCase().includes(query)));
        const value = (s: ServiceListItem): number | string => {
            switch (sort.key) {
                case "risk": return riskScore(severityCounts(findingsFor(s))) * 1000 + findingsFor(s).length;
                case "findings": return findingsFor(s).length;
                case "port": return s.port;
                case "service": return serviceLabel(s);
                case "host": return hostLabel(s);
            }
        };
        return [...filtered].sort((a, b) => {
            const va = value(a), vb = value(b);
            const cmp = typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb));
            return (sort.dir === "asc" ? cmp : -cmp) || a.port - b.port || a.host.localeCompare(b.host);
        });
    }, [services, search, protocolFilter, portGroup, sort, insights, findingsFor, hostLabel]);

    const rows = useMemo(() => {
        if (view === "list") return visibleServices.map((svc) => ({ kind: "row" as const, svc, key: svc.id }));
        const groups = new Map<string, ServiceListItem[]>();
        for (const svc of visibleServices) {
            const groupKey = view === "port" ? portLabel(svc) : hostLabel(svc);
            groups.set(groupKey, [...(groups.get(groupKey) ?? []), svc]);
        }
        return [...groups.entries()].flatMap(([groupKey, items]) => [
            { kind: "heading" as const, label: groupKey, count: items.length, key: `h:${groupKey}` },
            ...items.map((svc) => ({ kind: "row" as const, svc, key: `${groupKey}>${svc.id}` })),
        ]);
    }, [view, visibleServices, hostLabel]);

    function toggleSort(key: SortKey) {
        setSort((prev) => prev.key === key
            ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
            : { key, dir: key === "risk" || key === "findings" ? "desc" : "asc" });
    }
    const sortSelectValue = `${sort.key}:${sort.dir}`;
    const filtersActive = Boolean(search.trim()) || protocolFilter !== "all" || portGroup !== "all";
    const clearFilters = () => { setSearch(""); setProtocolFilter("all"); setPortGroup("all"); };
    const openService = openServiceId ? services.find((s) => s.id === openServiceId) ?? null : null;

    const SortHeader = ({ label, sortKey }: { label: string; sortKey?: SortKey }) => sortKey ? (
        <button type="button" onClick={() => toggleSort(sortKey)}
            className={cn("flex items-center gap-1 text-left uppercase hover:text-foreground", sort.key === sortKey && "text-brand-cyan")}>
            {label}
            {sort.key === sortKey && <span aria-hidden="true">{sort.dir === "asc" ? "▲" : "▼"}</span>}
        </button>
    ) : <span>{label}</span>;

    return (
        <section className="min-w-0 pt-6" data-scan-id={scanId}>
            <div className="mb-4 grid grid-cols-[max-content_max-content_minmax(400px,1fr)] items-center gap-7 max-[1450px]:grid-cols-[auto_minmax(0,1fr)] max-[1100px]:flex max-[1100px]:flex-col max-[1100px]:items-stretch">
                <div>
                    <div className="flex items-center gap-2.5">
                        <h2 className="m-0 text-[25px] text-foreground">Services</h2>
                        <span className="rounded-full bg-[#172338] px-2.5 py-1 text-[13px] text-[#dbeafe]">{services.length}</span>
                    </div>
                    <p className="mt-2 text-[13px] text-muted-foreground">
                        {services.length} {allOpen ? "open " : ""}port{services.length === 1 ? "" : "s"} on {hostCount} host{hostCount === 1 ? "" : "s"}
                    </p>
                </div>

                <SummaryCard
                    title="Services"
                    icon={Server}
                    accentClassName="bg-[#a855f7]/10 text-[#c084fc]"
                    value={services.length}
                    items={typeCounts.map(([label, value]) => ({ label, value }))}
                    colors={typeCounts.map((_, i) => CHART_COLORS[i % CHART_COLORS.length])}
                    keepBreakdownOnPhones
                    layout="side"
                    className="w-fit border"
                />

                <div className={cn(
                    "grid w-full max-w-[760px] gap-2 justify-self-end max-[1450px]:col-span-full max-[1450px]:max-w-none max-[1100px]:grid-cols-1 max-[720px]:grid-cols-[minmax(0,1fr)_auto]",
                    protocols.length > 1
                        ? "grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)] max-[1450px]:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)]"
                        : "grid-cols-1 max-[1450px]:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]",
                )}>
                    <label className={cn("flex min-h-10 items-center gap-2.5 rounded-lg border border-brand-panel-border bg-brand-panel-deep px-3.5", protocols.length > 1 && "col-span-2 max-[1450px]:col-span-1")}>
                        <span aria-hidden="true" className="text-muted-foreground">⌕</span>
                        <input
                            type="search"
                            placeholder="Search port, service, host or product..."
                            aria-label="Search services"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            autoCapitalize="off"
                            autoCorrect="off"
                            className="w-full border-0 bg-transparent text-foreground outline-none"
                        />
                    </label>
                    <FilterSheet activeCount={Number(protocolFilter !== "all") + Number(sortSelectValue !== "risk:desc")}>
                        {protocols.length > 1 && (
                            <select aria-label="Protocol" value={protocolFilter} onChange={(e) => setProtocolFilter(e.target.value)} className={selectClassName}>
                                <option value="all">Protocol: All</option>
                                {protocols.map((p) => <option key={p} value={p}>{p}</option>)}
                            </select>
                        )}
                        <select
                            aria-label="Sort services"
                            value={sortSelectValue}
                            onChange={(e) => { const [key, dir] = e.target.value.split(":"); setSort({ key: key as SortKey, dir: dir as SortDir }); }}
                            className={selectClassName}
                        >
                            <option value="risk:desc">Sort: Riskiest first</option>
                            <option value="port:asc">Sort: Port</option>
                            <option value="service:asc">Sort: Service</option>
                            <option value="host:asc">Sort: Host</option>
                            <option value="findings:desc">Sort: Most findings</option>
                        </select>
                    </FilterSheet>
                </div>
            </div>

            {error && <p className="mt-4 text-xs text-muted-foreground">{error}</p>}
            {loading && <p className="mt-4 text-xs text-muted-foreground">Loading services...</p>}

            {!loading && !error && (
                <>
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-1.5">
                            {[{ key: "all", label: "All", count: services.length }, ...PORT_GROUPS.map((g) => ({ key: g.key, label: g.label, count: portGroupCounts[g.key] }))]
                                .filter((g) => g.key === "all" || g.count > 0)
                                .map((g) => (
                                    <button key={g.key} type="button" onClick={() => setPortGroup(g.key)} aria-pressed={portGroup === g.key}
                                        className={cn("rounded-full border px-2.5 py-0.5 text-[11px] font-semibold",
                                            portGroup === g.key ? "border-brand-cyan/60 bg-brand-cyan/10 text-brand-cyan" : "border-brand-panel-border text-[#94a3b8] hover:text-foreground")}>
                                        {g.label} <span className="opacity-70">{g.count}</span>
                                    </button>
                                ))}
                            {allOpen && protocols.length === 1 && (
                                <span className="ml-1 text-[11px] text-[#64748b]">All services are open {protocols[0]}</span>
                            )}
                        </div>
                        <span className="inline-flex overflow-hidden rounded-md border border-brand-panel-border">
                            {([["list", "List"], ["port", "By port"], ["host", "By host"]] as const).map(([key, label]) => (
                                <button key={key} type="button" onClick={() => setView(key)} aria-pressed={view === key}
                                    className={cn("px-2.5 py-1 text-[11px] font-semibold", view === key ? "bg-brand-cyan/10 text-brand-cyan" : "text-[#94a3b8] hover:text-foreground")}>
                                    {label}
                                </button>
                            ))}
                        </span>
                    </div>

                    {visibleServices.length === 0 ? (
                        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-brand-panel-border px-4 py-8 text-center">
                            <p className="m-0 text-sm text-muted-foreground">
                                {search.trim() ? <>No services match &ldquo;{search.trim()}&rdquo;.</> : services.length === 0 ? "No open ports were found." : "No services match your filters."}
                            </p>
                            {filtersActive && (
                                <button type="button" onClick={clearFilters} className="text-xs font-semibold text-brand-cyan hover:underline">Clear filters</button>
                            )}
                        </div>
                    ) : (
                        <div className="min-w-0 overflow-x-auto border-t border-b border-brand-panel-border max-[720px]:overflow-visible max-[720px]:border-0">
                            <div className={cn(ROW_GRID, "min-w-[980px] border-b border-brand-panel-border px-4 py-2.5 text-[10px] font-semibold tracking-wide text-[#94a3b8] max-[720px]:hidden")}>
                                <SortHeader label="Port" sortKey="port" />
                                <SortHeader label="Service" sortKey="service" />
                                <SortHeader label="Host" sortKey="host" />
                                <SortHeader label="Product / version" />
                                <span>TLS</span>
                                <SortHeader label="Findings" sortKey="risk" />
                                <span />
                            </div>

                            <div className="max-[720px]:flex max-[720px]:flex-col max-[720px]:gap-2">
                                {rows.map((row) => {
                                    if (row.kind === "heading") {
                                        return (
                                            <div key={row.key} className="border-b border-brand-panel-border bg-white/[0.02] px-4 py-1.5 text-[11px] font-semibold text-[#cbd5e1] max-[720px]:border-0 max-[720px]:bg-transparent max-[720px]:px-1 max-[720px]:pt-2">
                                                {row.label} <span className="font-normal text-[#94a3b8]">· {row.count} service{row.count === 1 ? "" : "s"}</span>
                                            </div>
                                        );
                                    }
                                    const { svc } = row;
                                    const info = insights.get(svc.id);
                                    const svcFindings = findingsFor(svc);
                                    return (
                                        <button
                                            key={row.key}
                                            type="button"
                                            onClick={() => setOpenServiceId(svc.id)}
                                            aria-haspopup="dialog"
                                            className={cn(
                                                "w-full border-0 border-b border-[#243047]/[0.76] bg-transparent text-left text-[#cbd5e1] transition-colors last:border-b-0 hover:bg-[#0d1928]",
                                                openServiceId === svc.id && "bg-[#0d1928] shadow-[inset_2px_0_#258cff]",
                                                "max-[720px]:rounded-lg max-[720px]:border max-[720px]:border-brand-panel-border max-[720px]:bg-brand-panel max-[720px]:last:border-b",
                                            )}
                                        >
                                            <span className={cn(ROW_GRID, "min-w-[980px] px-4 py-2.5 text-[12px] max-[720px]:hidden")}>
                                                <PortChip svc={svc} />
                                                <ServiceName svc={svc} />
                                                <span className="min-w-0 truncate" title={hostLabel(svc)}>
                                                    <span className="text-foreground">{svc.host}</span>
                                                    {info && info.hostnames.length > 0 && <span className="text-[#94a3b8]"> · {info.hostnames.join(", ")}</span>}
                                                </span>
                                                <span className="min-w-0 truncate text-[#cbd5e1]" title={productLabel(svc) || info?.techs.join(", ")}>
                                                    {productLabel(svc) || info?.techs[0] || <span className="text-[#64748b]">—</span>}
                                                </span>
                                                <span>{info?.tls ? <Lock className="size-3.5 text-brand-success" aria-label="TLS" /> : <span className="text-[#64748b]">—</span>}</span>
                                                <FindingsSummary findings={svcFindings} />
                                                <ChevronRight className="size-4 text-[#64748b]" aria-hidden="true" />
                                            </span>

                                            <span className="hidden flex-col gap-1.5 p-3 max-[720px]:flex">
                                                <span className="flex items-start justify-between gap-2">
                                                    <span className="flex items-center gap-2 text-sm"><PortChip svc={svc} /><ServiceName svc={svc} /></span>
                                                    {info?.tls && <Lock className="size-3.5 shrink-0 text-brand-success" aria-label="TLS" />}
                                                </span>
                                                <span className="truncate text-[11px] text-[#94a3b8]">{hostLabel(svc)}{productLabel(svc) ? ` · ${productLabel(svc)}` : ""}</span>
                                                <span className="flex items-center justify-between gap-2">
                                                    <FindingsSummary findings={svcFindings} />
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

            {openService && (
                <ServiceDetails service={openService} scanId={scanId} info={insights.get(openService.id)} onClose={closeService} />
            )}
        </section>
    );
}

function ServiceDetails({
    service,
    scanId,
    info,
    onClose,
}: {
    service: ServiceListItem;
    scanId: string;
    info: ServiceInsight | undefined;
    onClose: () => void;
}) {
    const findings = useMemo(() => info?.findings ?? [], [info]);
    const counts = severityCounts(findings);
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
    const box = "rounded-md border border-[#26364e] bg-[#091523] px-2 py-0.5 text-[11px]";

    return (
        <SidePanelShell labelledBy="service-details-title" onClose={onClose}>
            <header className="flex items-start justify-between gap-3 border-b border-brand-panel-border p-4">
                <div className="min-w-0">
                    <h2 id="service-details-title" className="m-0 flex flex-wrap items-center gap-2 text-base leading-snug font-semibold tracking-normal! text-foreground [font-family:inherit]!">
                        <span className="font-mono">{portLabel(service)}</span>
                        <ServiceName svc={service} />
                    </h2>
                    <p className="m-0 mt-0.5 text-[11px] break-all text-[#94a3b8]">{service.host}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        {info?.tls && (
                            <span className="inline-flex items-center gap-1 rounded-[5px] border border-brand-success/50 bg-brand-success/10 px-1.5 py-px text-[10px] font-bold text-brand-success">
                                <Lock className="size-3" /> TLS
                            </span>
                        )}
                        <span className="rounded-[5px] border border-[#26364e] px-1.5 py-px text-[10px] font-semibold text-[#cbd5e1] capitalize">{service.state}</span>
                        {SEVERITIES.filter((s) => counts[s] > 0).map((s) => (
                            <span key={s} className={cn("rounded-[5px] border px-1.5 py-px text-[10px] font-bold", SEVERITY_BADGE[s])}>{counts[s]} {capitalize(s)}</span>
                        ))}
                    </div>
                </div>
                <button type="button" onClick={onClose} aria-label="Close service details"
                    className="grid size-8 shrink-0 place-items-center rounded-lg text-[#94a3b8] hover:bg-white/5 hover:text-foreground">
                    <X className="size-4" />
                </button>
            </header>

            <div className="min-h-0 overflow-y-auto overscroll-contain p-4">
                <div className="flex flex-col gap-4 rounded-lg border border-[#22324d] bg-[#0f1c30] p-4">
                    {isUnknownService(service.service_name) && (
                        <p className="m-0 flex gap-2 rounded-md border border-[#26364e] bg-[#091523] p-2.5 text-[11px] leading-relaxed text-[#cbd5e1]">
                            <Info className="mt-px size-3.5 shrink-0 text-[#94a3b8]" /> {TCPWRAPPED_HELP}
                        </p>
                    )}

                    <section>
                        <h3 className={section}>Host</h3>
                        <div className="flex flex-wrap gap-1.5">
                            {[service.host, ...(info?.hostnames ?? [])].map((name) => (
                                <Link key={name} href={`/phase2_scan/results/${scanId}/assets?asset=${encodeURIComponent(name)}`}
                                    className={cn(box, "text-brand-cyan no-underline hover:border-brand-cyan")}>
                                    {name}
                                </Link>
                            ))}
                        </div>
                    </section>

                    <section>
                        <h3 className={section}>Product / version</h3>
                        <p className="m-0 text-[12px] text-[#cbd5e1]">{productLabel(service) || "Not identified"}</p>
                    </section>

                    {service.banner && (
                        <section>
                            <h3 className={section}>Banner</h3>
                            <pre className="m-0 rounded-md border border-[#26364e] bg-[#091523] p-2 font-mono text-[11px] whitespace-pre-wrap [overflow-wrap:anywhere] text-[#cbd5e1]">{service.banner}</pre>
                        </section>
                    )}

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
                            <p className="m-0 text-[12px] text-[#64748b]">No findings on this port.</p>
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

                    <section>
                        <h3 className={section}>Detected on</h3>
                        <p className="m-0 text-[12px] text-[#cbd5e1]">{formatDateTime(service.created_at)}</p>
                    </section>

                    <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-[#22324d] pt-3">
                        {info?.nodeId && (
                            <Link href={`/phase2_scan/results/${scanId}/graph?node=${encodeURIComponent(info.nodeId)}`}
                                className="inline-flex items-center gap-1 text-[11px] font-semibold text-brand-cyan no-underline hover:underline">
                                View on graph <ChevronRight className="size-3.5" />
                            </Link>
                        )}
                        <Link href={`/phase2_scan/results/${scanId}/assets?asset=${encodeURIComponent(service.host)}`}
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-brand-cyan no-underline hover:underline">
                            View host <ChevronRight className="size-3.5" />
                        </Link>
                    </div>
                </div>
            </div>
        </SidePanelShell>
    );
}