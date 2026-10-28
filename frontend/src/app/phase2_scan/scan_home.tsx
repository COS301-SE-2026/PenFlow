"use client"

import { useEffect, useState } from "react" ;
import  {useRouter } from "next/navigation";
import Link from "next/link" ;
import {Check, Globe , Crosshair , CheckCircle2,XCircle , Clock , MoreVertical , ChevronRight, ArrowUpDown, Plus, Satellite, Search, ShieldAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import {Card , CardContent} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Separator} from "@/components/ui/separator";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils"
import { postScanRequest,fetchScanHistory, type ScanHistoryItem} from "@/lib/scanService";
import { fetch_domains,type domain_item } from "@/lib/domainServices";
import PageHero from "@/shared/components/PageHero";
import DomainLastScanPanel from "./DomainLastScanPanel";
import { validateDomain } from "@/lib/domainValidator";
import { formatDateWithYear } from "@/lib/engagementFormat";


type ScanMode = "active" | "passive" ;

const scanTypeLabel: Record<string, string> = {
    active_vulnerability: "Active Vulnerability Scan",
    passive_ctem: "Passive Reconnaissance",
};

const RUNNING_STATUSES = new Set(["queued", "running"]);

const statusConfig: Record<string, { label: string; className: string; icon:LucideIcon }> = {
    running: { label: "Running", className: "border-brand-cyan text-brand-cyan bg-brand-cyan/10" ,icon: Globe },
    queued: { label: "Queued", className: "border-brand-yellow text-brand-yellow bg-brand-yellow/10", icon: Clock},
    completed: {label: "Completed", className: "border-brand-success text-brand-success bg-brand-success/10", icon: CheckCircle2},
    failed: {label: "Failed", className: "border-brand-alert text-brand-alert bg-brand-alert/10", icon: XCircle},
    partial: {label: "Partial", className: "border-brand-yellow text-brand-yellow bg-brand-yellow/10", icon: XCircle} ,
};



function StatusBadge({ status }: { status: string}) {
        const config = statusConfig[status] ?? statusConfig.queued;
        return (
            <div className="flex shrink-0 justify-center sm:w-28">
                <Badge variant = "outline" className={(cn("uppercase tracking-wide",config.className))}>
                    {config.label}                
                </Badge>
            </div>
            
    );
}

function ScanIcon ({ status }: { status: string}){
        const config = statusConfig[status] ?? statusConfig.queued;
        const Icon = config.icon;
        return(
            <div className ={cn("flex size-9 shrink-0 items-center justify-center rounded-full bg-muted sm:size-11",config.className)}>
                <Icon className = "size-4 sm:size-5"/>
            </div>
        );
}

function MoreMenuButton(){
    return(
        <Button variant = "ghost" size = "icon" aria-label ="More options">
            <MoreVertical className= "size-4"/>    
        </Button>
    );
}

function TextLink({children, href}:{children: React.ReactNode; href:string }){
    return(
        <Link href = {href} className="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-brand-cyan hover:underline">
            {children}
            <ChevronRight className = "size-4"/>
        </Link>
    );
}

function SectionHeader( {title, count }: {title:string; count: number}){
    return (
        <div className="mb-4 flex items-center gap-2">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground">{title}</h2>
            <span className="flex size-5 items-center justify-center rounded-full bg-muted text-xs text-muted-foreground">
                {count}
            </span>
        </div>
    );
}
const modeTheme:Record<
    ScanMode,
    {
        icon : LucideIcon;
        title: string;
        description: string;
        selectedCardClass: string;
        ringClass :string;
        buttonClass: string;
        mutedButtonClass: string;
        chipClass:string;
        selectedTileClass: string;
    }
> = {
    active:{
        icon: Crosshair,
        title: "Active scan",
        description: "Probes ports, services and known vulnerabilities on a domain you own.",
        selectedCardClass: "border-brand-cyan/60 bg-brand-cyan/[0.05] shadow-[0_0_28px_-10px_rgba(43,216,245,0.45)]",
        ringClass: "border-brand-panel-border focus-visible:border-brand-cyan/70 focus-visible:ring-brand-cyan/20",
        buttonClass: "bg-brand-cyan text-[#04121f] hover:bg-brand-cyan/85 shadow-[0_0_18px_-4px_rgba(43,216,245,0.6)]",
        mutedButtonClass: "bg-brand-cyan/60 text-[#04121f]",
        chipClass:"border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan",
        selectedTileClass: "border-brand-cyan/60 bg-brand-cyan/[0.06]",
    },
    passive:{
        icon: Satellite,
        title: "Passive scan",
        description: "Looks only at public records like DNS, certificates and breach data.",
        selectedCardClass: "border-[#a78bfa]/60 bg-[#a78bfa]/[0.05] shadow-[0_0_28px_-10px_rgba(167,139,250,0.45)]",
        ringClass: "border-brand-panel-border focus-visible:border-[#a78bfa]/70 focus-visible:ring-[#a78bfa]/20",
        buttonClass: "bg-[#a78bfa] text-[#1e1240] hover:bg-[#a78bfa]/85 shadow-[0_0_18px_-4px_rgba(167,139,250,0.6)]",
        mutedButtonClass: "bg-[#a78bfa]/60 text-[#1e1240]",
        chipClass:"border-[#a78bfa]/30 bg-[#a78bfa]/10 text-[#a78bfa]",
        selectedTileClass: "border-[#a78bfa]/60 bg-[#a78bfa]/[0.06]",
    },
};

function riskFor(scan: ScanHistoryItem) {
    const score = Math.min(100, scan.critical_count * 25 + scan.high_count * 15 + scan.medium_count * 5 + scan.low_count);
    if (score >= 70) return { score, label: "High", className: "border-brand-alert/40 bg-brand-alert/10 text-brand-alert" };
    if (score >= 40) return { score, label: "Medium", className: "border-brand-yellow/40 bg-brand-yellow/10 text-brand-yellow" };
    return { score, label: "Low", className: "border-brand-success/40 bg-brand-success/10 text-brand-success" };
}

const FINISHED_STATUSES = new Set(["completed", "partial"]);

type DomainSort = "recent" | "az";
const DOMAIN_SORTS: { value: DomainSort; label: string }[] = [
    { value: "recent", label: "Recently Added" },
    { value: "az", label: "A - Z" },
];

function latestScans(scans: ScanHistoryItem[]): Map<string, ScanHistoryItem> {
    const latest = new Map<string, ScanHistoryItem>();
    for (const scan of scans) {
        if (!FINISHED_STATUSES.has(scan.status)) continue;
        const key = scan.domain.toLowerCase();
        const current = latest.get(key);
        if (!current || scan.created_at > current.created_at) latest.set(key, scan);
    }
    return latest;
}

function ScanModeCards({ mode, onChange }: { mode: ScanMode; onChange: (mode: ScanMode) => void }) {
    return (
        <div role="radiogroup" aria-label="Scan type" className="mx-auto grid w-full max-w-[900px] grid-cols-2 gap-3 max-sm:grid-cols-1">
            {(["active", "passive"] as const).map((option) => {
                const theme = modeTheme[option];
                const OptionIcon = theme.icon;
                const selected = mode === option;
                return (
                    <button
                        key={option}
                        type="button"
                        role="radio"
                        aria-checked={selected}
                        onClick={() => onChange(option)}
                        className={cn(
                            "relative flex items-start gap-3 rounded-xl border p-4 text-left transition-all duration-200",
                            selected ? theme.selectedCardClass : "border-brand-panel-border bg-brand-panel-deep/40 opacity-70 hover:opacity-100 hover:border-brand-panel-border/80"
                        )}
                    >
                        <span className={cn("flex size-10 shrink-0 items-center justify-center rounded-lg border", theme.chipClass)}>
                            <OptionIcon className="size-5" />
                        </span>
                        <span className="min-w-0 flex-1">
                            <span className="block text-sm font-semibold text-foreground">{theme.title}</span>
                            <span className="mt-0.5 block text-xs text-muted-foreground">{theme.description}</span>
                        </span>
                    </button>
                );
            })}
        </div>
    );
}

function NewScanForm({ scans }: { scans: ScanHistoryItem[] }) {
    const router = useRouter();
    const [mode, setMode] = useState <ScanMode>("active");
    const [activeDomainId , setActiveDomainId] = useState("");
    const [passiveDomain , setPassiveDomain] = useState("");
    const [domainSearch, setDomainSearch] = useState("");
    const [domainSort, setDomainSort] = useState<DomainSort>("recent");
    const [panelView, setPanelView] = useState<ScanMode>("active");
    const [verifiedDomains ,setVerifiedDomains] = useState<domain_item[]>([]);
    const [loadingDomains, setLoadingDomains] = useState(true);
    const [submitting, setsubmitting] = useState(false);
    const [formError,setFormError] = useState<string | null> (null);

    useEffect( () => {
        fetch_domains ({status: "verified",limit: 100})
            .then((result) => setVerifiedDomains(result.items))
            .catch(()=> setVerifiedDomains([]))
            .finally(()=> setLoadingDomains(false));
    },[]);

    const lastScans = latestScans(scans);
    const activeDomain = verifiedDomains.find((d)=> d.id === activeDomainId);
    const passiveCheck = passiveDomain.trim() ? validateDomain(passiveDomain) : null;
    const passiveCleaned = passiveCheck?.valid && passiveCheck.domain !== passiveDomain.trim().toLowerCase() ? passiveCheck.domain : null;
    const domain = mode === "active" ? (activeDomain?.domain ?? "") : (passiveCheck?.valid ? passiveCheck.domain : "");
    const theme = modeTheme[mode];
    const filteredDomains = verifiedDomains
        .filter((d) => d.domain.toLowerCase().includes(domainSearch.trim().toLowerCase()))
        .sort((a, b) => domainSort === "az" ? a.domain.localeCompare(b.domain) : b.created_at.localeCompare(a.created_at));

    async function handleStart(forMode: ScanMode = mode, target: string = domain){
            if (!target || submitting) return ;
            setsubmitting(true);
            setFormError(null);
            try {
                const { scan_id } = await postScanRequest({
                    domain: target,
                    scan_type: forMode === "active" ? "active_vulnerability" : "passive_ctem",
                    verified_domain_id: forMode === "active" ? activeDomainId : undefined
            });
            router.push(`/phase2_scan/progress?scan_id=${scan_id}`);
        }catch (err){
            setFormError(err instanceof Error ? err.message : "Failed to start scan");
        } finally {
            setsubmitting(false);
        }
    }

    const startButton = (className?: string, forMode: ScanMode = mode) => {
        const buttonTheme = modeTheme[forMode];
        const target = forMode === mode ? domain : (activeDomain?.domain ?? "");
        const enabled = target !== "" && !submitting;
        const Icon = forMode === "passive" ? Satellite : buttonTheme.icon;
        return (
            <Button
                disabled={!enabled}
                onClick={()=> void handleStart(forMode, target)}
                className={cn("h-10 gap-2 px-5 max-sm:h-11 max-sm:w-full", enabled ? buttonTheme.buttonClass : buttonTheme.mutedButtonClass, className)}
            >
                <Icon className="size-4" />
                {submitting ? "Starting..." : `Start ${forMode} scan`}
            </Button>
        );
    };

    return (
        <Card className="border border-brand-panel-border bg-gradient-to-br from-brand-panel to-brand-panel-deep ring-0">
            <CardContent className="flex flex-col gap-5">
                <div>
                    <h2 className="text-sm font-semibold tracking-wide text-foreground uppercase [font-family:inherit]!">New Scan</h2>
                    <p className="text-xs text-muted-foreground">Choose a scan type, then the domain to scan.</p>
                </div>

                <ScanModeCards mode={mode} onChange={(next) => { setMode(next); setFormError(null); }} />

                <Separator className="bg-brand-panel-border"/>

                {mode === "active" ? (
                    <div className="flex flex-col gap-3">
                    <div className="flex items-start gap-5 max-xl:flex-col max-xl:items-stretch">
                    <div className="flex w-full max-w-[520px] shrink-0 flex-col gap-3 max-xl:max-w-none">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex w-full max-w-[520px] items-center gap-2 max-xl:max-w-none max-sm:flex-wrap">
                            <Label className="shrink-0">Verified domain</Label>
                            {verifiedDomains.length > 0 && (
                                <div className="ml-auto flex items-center gap-2 max-sm:ml-0 max-sm:w-full">
                                    <div className="relative w-44 max-sm:flex-1">
                                        <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                                        <Input
                                            type="search"
                                            aria-label="Search verified domains"
                                            placeholder="Search..."
                                            value={domainSearch}
                                            onChange={(e) => setDomainSearch(e.target.value)}
                                            className={cn("h-9 pl-9 max-sm:h-10 max-sm:text-base", theme.ringClass)}
                                        />
                                    </div>
                                    <Select value={domainSort} onValueChange={(value) => setDomainSort(value as DomainSort)}>
                                        <SelectTrigger aria-label="Sort domains" className={cn("h-9 w-auto min-w-36 gap-1.5 max-sm:h-10", theme.ringClass)}>
                                            <ArrowUpDown className="size-4 text-muted-foreground" />
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent align="end">
                                            {DOMAIN_SORTS.map((option) => (
                                                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            )}
                        </div>
                        {activeDomain && startButton("max-sm:order-last sm:hidden", panelView)}
                    </div>
                        {loadingDomains ? (
                            <div className="flex w-full flex-col gap-2.5">
                                {[0, 1, 2].map((i) => <div key={i} className="h-[62px] animate-pulse rounded-lg border border-brand-panel-border bg-white/[0.02]" />)}
                            </div>
                        ) : verifiedDomains.length === 0 ? (
                            <div className="flex items-center gap-4 rounded-xl border border-dashed border-brand-panel-border bg-white/[0.02] p-4 max-sm:flex-col max-sm:items-stretch">
                                <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-brand-yellow/10 text-brand-yellow max-sm:hidden">
                                    <ShieldAlert className="size-5" />
                                </span>
                                <div className="min-w-0 flex-1">
                                    <p className="text-sm font-medium text-foreground">You need a verified domain to run an active scan</p>
                                    <p className="text-xs text-muted-foreground">Add a domain and verify you own it, or run a passive scan on any domain now.</p>
                                </div>
                                <div className="flex shrink-0 gap-2 max-sm:flex-col">
                                    <Button asChild variant="outline" className="gap-1.5">
                                        <Link href="/domains"><Plus className="size-4" />Add a domain</Link>
                                    </Button>
                                    <Button variant="ghost" onClick={() => setMode("passive")} className="gap-1.5 text-[#a78bfa] hover:text-[#c4b5fd]">
                                        <Satellite className="size-4" />Passive scan instead
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            <div role="radiogroup" aria-label="Verified domain" className="flex w-full flex-col gap-2.5">
                                {filteredDomains.map((verifiedDomain) => {
                                    const selected = verifiedDomain.id === activeDomainId;
                                    const last = lastScans.get(verifiedDomain.domain.toLowerCase());
                                    const risk = last ? riskFor(last) : null;
                                    return (
                                        <button
                                            key={verifiedDomain.id}
                                            type="button"
                                            role="radio"
                                            aria-checked={selected}
                                            onClick={() => { setActiveDomainId(selected ? "" : verifiedDomain.id); setPanelView("active"); setFormError(null); }}
                                            className={cn(
                                                "flex items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors",
                                                selected ? theme.selectedTileClass : "border-brand-panel-border bg-brand-panel-deep/40 hover:bg-white/[0.03]"
                                            )}
                                        >
                                            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-brand-success/30 bg-brand-success/10 text-brand-success">
                                                <Globe className="size-4" />
                                            </span>
                                            <span className="min-w-0 flex-1">
                                                <span className="block truncate text-sm font-medium text-foreground">{verifiedDomain.domain}</span>
                                                <span className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                                                    {last && risk ? (
                                                        <>
                                                            Last scanned {formatDateWithYear(last.created_at)}
                                                            <span className={cn("rounded-full border px-1.5 text-[10px] font-semibold", risk.className)}>{risk.score} · {risk.label}</span>
                                                        </>
                                                    ) : "Never scanned"}
                                                </span>
                                            </span>
                                            {selected && <CheckCircle2 aria-hidden="true" className="size-4 shrink-0 text-brand-cyan" />}
                                        </button>
                                    );
                                })}
                                {filteredDomains.length === 0 && (
                                    <div className="flex items-center justify-between gap-3 rounded-lg border border-dashed border-brand-panel-border px-3 py-3 text-sm text-muted-foreground">
                                        No verified domains match &quot;{domainSearch.trim()}&quot;.
                                        <button type="button" onClick={() => setDomainSearch("")} className="shrink-0 font-medium text-brand-cyan hover:underline">
                                            Clear
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                    {activeDomain && (
                        <div className="min-w-0 flex-1">
                            <DomainLastScanPanel
                                key={activeDomain.id}
                                domain={activeDomain.domain}
                                scans={scans}
                                view={panelView}
                                onViewChange={setPanelView}
                                action={startButton("max-sm:hidden", panelView)}
                            />
                        </div>
                    )}
                    </div>
                    </div>
                ) : (
                    <div className="flex flex-col gap-1.5 sm:mx-auto sm:w-fit sm:max-w-full">
                        <Label htmlFor="passive-domain">Domain</Label>
                        <div className="flex items-center gap-3">
                        <div className="relative w-full sm:w-[520px] sm:max-w-[calc(100vw-22rem)]">
                            <Globe className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                            <Input
                                id="passive-domain"
                                placeholder="example.com"
                                value={passiveDomain}
                                onChange={(e)=> { setPassiveDomain(e.target.value); setFormError(null); }}
                                onKeyDown={ (e) => {
                                    if(e.key === "Enter") void handleStart();
                                }}
                                inputMode="url"
                                autoCapitalize="off"
                                autoCorrect="off"
                                spellCheck={false}
                                aria-invalid={passiveCheck && !passiveCheck.valid ? true : undefined}
                                className={cn(
                                    "h-10 pr-9 pl-9 max-sm:h-11 max-sm:text-base",
                                    theme.ringClass,
                                    passiveCheck && !passiveCheck.valid && "border-brand-alert/60",
                                    passiveCheck?.valid && "border-brand-success/50"
                                )}
                            />
                            {passiveCheck?.valid && <Check aria-hidden="true" className="absolute top-1/2 right-3 size-4 -translate-y-1/2 text-brand-success" />}
                        </div>
                        {startButton("shrink-0 max-sm:w-auto")}
                        </div>
                        <p className={cn("text-xs", passiveCheck && !passiveCheck.valid ? "text-brand-alert" : "text-muted-foreground")}>
                            {passiveCheck && !passiveCheck.valid
                                ? passiveCheck.error
                                : passiveCleaned
                                    ? <>Will scan: <span className="font-medium text-foreground">{passiveCleaned}</span></>
                                    : "Public records only, so you don't need to verify ownership. Pasted URLs are cleaned up for you."}
                        </p>
                    </div>
                )}

                {formError && <p className="text-xs text-brand-alert">{formError}</p>}

            </CardContent>
        </Card>
    );
}


export default function ScanHome() {
    const [scans, setScans] = useState<ScanHistoryItem[]>([]);
    const [loading , setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchScanHistory()
            .then(setScans)
            .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load scans"))
            .finally(()=>setLoading(false));
    },[]);
    const runningScans = scans.filter((s)=> RUNNING_STATUSES.has(s.status));
    
    return(
        <div className="flex flex-col gap-8">
            <PageHero title = "SCANS" />
            
            <NewScanForm scans={scans}/>

            {error && <p className="text-sm text-brand-alert">{error}</p>}
            {loading && <p className="text-sm text-muted-foreground">Loading Scans...</p>}

            {!loading && !error && (
                <>
                    <section>
                        <SectionHeader title="Running Scans" count={runningScans.length}/>
                        {runningScans.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No scans currently running.</p>
                        ): (
                            <div className="flex flex-col gap-3">
                                {runningScans.map((scan) => (
                                    <Card key = {scan.id} className="border border-brand-panel-border bg--brand-panel ring-0 [--card-spacing:--spacing(3)] sm:[--card-spacing:--spacing(4)]">
                                        <CardContent className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 sm:flex sm:flex-wrap sm:gap-4">
                                            <ScanIcon status= {scan.status}/>
                                            <div className="min-w-0 flex-1">
                                            <p className="truncate font-medium text-foreground">{scan.domain}</p>
                                            <p className="truncate text-sm text-muted-foreground">
                                                {scanTypeLabel[scan.scan_type] ?? scan.scan_type}
                                            </p>
                                        </div>
                                        <StatusBadge status= {scan.status}/>
                                        <div className="col-span-3 flex items-center gap-3 sm:contents">
                                            <div className="flex flex-1 items-center gap-3 sm:w-48 sm:flex-none sm:shrink-0">
                                                <Progress value={scan.progress} className="flex-1"/>
                                                <span className="w-10 shrink-0 text-right text-sm text-muted-foreground">
                                                    {scan.progress}%
                                                </span>
                                            </div>
                                            <TextLink href ={`/phase2_scan/progress?scan_id=${scan.id}`}>View Progress</TextLink>
                                            <MoreMenuButton/>
                                        </div>
                                    </CardContent>
                                </Card>
                                ))}
                            </div>
                        )}
                    </section>
                        
                    
                    </>
                    )}
                </div>
                );
}