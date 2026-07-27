"use client"

import { useEffect, useState } from "react" ;
import  {useRouter } from "next/navigation";
import Link from "next/link" ;
import {Globe , Zap , Eye, CheckCircle2,XCircle , Clock , MoreVertical , ChevronRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import {Card , CardContent} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Select , SelectContent ,SelectItem , SelectTrigger , SelectValue  } from "@/components/ui/select";
import { Separator} from "@/components/ui/separator";
import { cn } from "@/lib/utils"
import { postScanRequest,fetchScanHistory, type ScanHistoryItem} from "@/lib/scanService";
import { fetch_domains,type domain_item } from "@/lib/domainServices";
import { set } from "animejs";

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

function formatTimestamp(iso: string): string {
    return new Date(iso).toLocaleString("en-GB",{
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
    });
}

function StatusBadge({ status }: { status: string}) {
        const config = statusConfig[status] ?? statusConfig.queued;
        return (
            <div className="flex w-28 shrink-0 justify-center">
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
            <div className ={cn("flex size-11 shrink-0 items-center justify-center rounded-full bg-muted",config.className)}>
                <Icon className = "size-5"/>
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
//neon-yellow for aggressive/active scanning, light purple for passive
//reconnaissance - distinct enough at a glance that the form's whole
//accent (toggle,border glow, focus rings, submit button) shift with it
const modeTheme:Record<
    ScanMode,
    {
        icon : LucideIcon;
        toggleActiveClass:string;
        cardAccentClass:string;
        ringClass :string;
        buttonClass: string;
        chipClass:string;
    }
> = {
    active:{
        icon:Zap,
        toggleActiveClass: "bg-[#eaff3d] text-black shadow-[0_0_16px_rgba(234,255,61,0.55)]",
        cardAccentClass: "border-[#eaff3d]/30 shadow-[0_0_40px_-12px_rgba(234,255,61,0.35)]",
        ringClass: 
        "border-[#eaff3d]/60 focus-visible:border-[#eaff3d] focus-visible:ring-[#eaff3d]/25 data-[state=open]:border-[#eaff3d] data-[state=open]:ring-3 data-[state=open]:ring-[#eaff3d]/25",
        buttonClass: "bg-[#eaff3d] text-black hover:bg-[#d8ee1f]",
        chipClass:"border-[#eaff3d]/30 bg-[#eaff3d]/10 text-[#eaff3d]",
    },
    passive:{
        icon: Eye,
        toggleActiveClass: "bg-purple-300 text-purple-950 shadow-[0_0_16px_rgba(216,180,254,0.5)]",
        cardAccentClass: "border-purple-400/30 shadow-[0_0_40px_-12px_rgba(192,132,252,0.35)]",
        ringClass: "border-purple-300/60 focus-visible:border-purple-300 focus-visible:ring-purple-300/25",
        buttonClass: "bg-purple-300 text-purple-950 hover:bg-purple-200",
        chipClass:"border-purple-300/30 bg-purple-300/10 text-purple-300",
    },
};

function ScanModeToggle({ mode, onChange } : {mode: ScanMode; onChange:(mode: ScanMode)=> void }) {
    return (
        <div className="inline-flex shrink-0 rounded-lg border border-brand-panel-border bg-brand-panel-deep p-1">
        {(["active","passive" ] as const).map((option) => {  
            const  OptionIcon = modeTheme[option].icon;
            const selected = mode === option;
            return(
                <button
                    key = {option}
                    type="button"
                    aria--pressed = {selected}
                    onClick={()=> onChange(option)}
                    className = { cn(
                        "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium capitalize transition-all",
                        selected
                            ? modeTheme[option].toggleActiveClass
                            : "text-muted-foreground hover:text-foreground"   
                    )}   
                >
                    <OptionIcon className= "size-3.5"/>
                    {option}
                    </button>
            );
        })}
        </div>
    );
}

function NewScanForm() {
    const router = useRouter();
    const [mode, setMode] = useState <ScanMode>("active");
    const [activeDomainId , setActiveDomainId] = useState("");
    const [passiveDomain , setPassiveDomain] = useState("");
    const [verifiedDomains ,setVerifiedDomains] = useState<domain_item[]>([]);
    const [loadingDomains, setLoadingDomains] = useState(false);
    const [submitting, setsubmitting] = useState(false);
    const [formError,setFormError] = useState<string | null> (null);

    useEffect( () => {
        setLoadingDomains(true);
        fetch_domains ({status: "verified",limit: 100})
            .then((result) => setVerifiedDomains(result.items))
            .catch(()=> setVerifiedDomains([]))
            .finally(()=> setLoadingDomains(false));
},[]);

    const activeDomain = verifiedDomains.find((d)=> d.id === activeDomainId);
    const domain = mode === "active" ? (activeDomain?.domain?? "") :passiveDomain.trim();
    const canStart = domain !== "" && !submitting;
    const theme = modeTheme[mode];
    const ModeIcon = theme.icon;

    async function handleStart(){
            if (!canStart) return ;
            setsubmitting(true);
            setFormError(null);
            try {
                const { scan_id } = await postScanRequest({
                    domain, 
                    scan_type: mode === "active" ? "active_vulnerability" : "passive_ctem",
                    verified_domain_id: mode === "active" ? activeDomainId : undefined
            });
            router.push(`/phase2_scan/progress?scan_id = ${scan_id}`);
        }catch (err){
            setFormError(err instanceof Error ? err.message : "Failed to start scan");
        } finally {
            setsubmitting(false);
        }
    }

    return (
        <Card
            className= {cn(
                "border bg-gradient-to-br from-brand-panel to-brand-panel-deep ring-0 transition-colors duration-300",
                    theme.cardAccentClass
            )}
        >
            <CardContent className="flex flex-col gap-5">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-2.5">
                        <span
                            className= {cn(
                                    "flex size-8 items-center justify-center rounded-lg border transition-colors duration-300",
                                    theme.chipClass
                            )}
                        >
                            <ModeIcon className="size-4" />
                            </span>
                            <div>
                                <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground">
                                    New Scan
                                </h2>
                                <p className="text-xs text-muted-foreground">
                                        {mode === "active" ? "Aggressive, verified-target scanning" : "Passive, low-footprint reconnasissance"}
                                </p>
                            </div>
                        </div>
                        <ScanModeToggle mode = {mode} onChange={setMode} />
                        </div>

                        <Separator className="bg-brand-panel-border"/>

                        {mode === "active" ? ( 
                            <div className="flex flex-col gap-1.5">
                            <Label htmlFor="active-domain">Verified Domain</Label>
                            <Select value={activeDomainId} onValueChange={ setActiveDomainId}>
                                <SelectTrigger id = "active-domain" className={theme.ringClass}>
                                    <SelectValue
                                        placeholder = {loadingDomains ? "Loading verified domains ...": "Select a verified Domain"}
                                        />
                                        </SelectTrigger>
                                        <SelectContent>
                                                 {verifiedDomains.map((verifiedDomain) => (
                                                    <SelectItem key = {verifiedDomain.id} value = {verifiedDomain.id}>
                                                        {verifiedDomain.domain}
                                                        </SelectItem>
                                                 ))}
                                        </SelectContent>
                                    </Select>
                                    <p className ="text-xs text-muted-foreground">
                                        Active scans only target domains that have completed ownership verification.
                                        {!loadingDomains && verifiedDomains.length ===0 && (
                                            <>You don&apos;t have any verified domains yet.</> 
                                        )}
                                    </p> 
                                </div>
                        ):  (
                                <div className="flex flex-col gap-1.5">
                                <Label htmlFor = "passive-domain">Domain</Label>
                                <div className="relative">
                                <div className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground " />
                                    <Globe className="relative"/>
                                    <Input 
                                        id = "passive-domain"
                                        placeholder="example.com"
                                        value = {passiveDomain}
                                        onChange={(e)=> setPassiveDomain(e.target.value)}
                                        onKeyDown={ (e) => {
                                            if(e.key === "Enter") void handleStart();
                                        }}
                                        className={cn("h-10 pl-9",theme.ringClass)}
                                        />
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        Passive reconnaissance only touches public records, so ownership verification isn&apos;t 
                                        required.
                                    </p>
                                </div>
                            )}

                            {formError && <p className="text-xs text-brand-alert">{formError}</p>}
                                <div className="flex justify-end gap-2">
                                <Button disabled = {!canStart} onClick={()=> void handleStart()} className={cn(canStart && theme.buttonClass)}>
                                    {submitting ? "Starting...": "Start Scan"}
                                </Button>
                            </div>
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
    const latestResults = scans.filter ((s)=> !RUNNING_STATUSES.has(s.status));
    return(
        <div className="flex flex-col gap-8">
            <div>
                <h1 className="text-2xl font-semibold uppercase tracking-wide text-foreground">
                        Scans
                </h1> 
                <p className="mt-1 text-sm text-muted-foreground">
                    Start a new passive or active scan.
                </p>
            </div>

            <NewScanForm/>

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
                                    <Card key = {scan.id} className="border border-brand-panel-border bg--brand-panel ring-0">
                                        <CardContent className="flex flex-wrap items-center gap-4">
                                            <ScanIcon status= {scan.status}/>
                                            <div className="min-w-0 flex-1">
                                            <p className="truncate font-medium text-foreground">{scan.domain}</p>
                                            <p className="text-sm text-muted-foreground">
                                                {scanTypeLabel[scan.scan_type] ?? scan.scan_type}
                                            </p>
                                        </div>
                                        <StatusBadge status= {scan.status}/>
                                        <div className="flex w-48 shrink-0 items-center gap-3">
                                            <Progress value={scan.progress} className="flex-1"/>
                                            <span className="w-10 shrink-0 text-right text-sm text-muted-foreground">
                                                {scan.progress}%
                                            </span>
                                        </div>
                                        <TextLink href ={`/phase2_scan/progress?scan_id=${scan.id}`}>View Progress</TextLink>
                                        <MoreMenuButton/>
                                    </CardContent>
                                </Card>
                                ))}
                            </div>
                        )}
                    </section>
                        
                    <section>
                        <SectionHeader title="Latest Results" count= {latestResults.length}/>
                        {latestResults.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No completed scans yet.</p>
                        ) : (
                            <div className="flex flex-col gap-3">
                                {latestResults.map((scan) =>  (
                                    <Card key={scan.id} className="border border-brand-panel-border bg-brand-panel ring-0">     
                                        <CardContent className="flex flex-wrap items-center gap-4">
                                            <ScanIcon status= {scan.status} />
                                            <div className="min-w-0 flex-1">
                                              <p className="truncate font-medium text-foreground">{scan.domain}</p>
                                              <p className="text-sm text-muted-foreground">
                                                {scanTypeLabel[scan.scan_type] ?? scan.scan_type}
                                              </p>
                                            </div>
                                              <StatusBadge status={scan.status}/>
                                              <span className="w-40 shrink-0 text-sm text-muted-foreground">
                                                {formatTimestamp(scan.created_at)}
                                              </span>
                                              <TextLink href={`/phase2_scan/results/${scan.id}`}>View Results </TextLink>
                                              <MoreMenuButton/>
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
