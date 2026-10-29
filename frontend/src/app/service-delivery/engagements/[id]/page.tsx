"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import ServiceDeliveryPageTitle from "@/shared/components/ServiceDeliveryPageTitle";
import ServiceDeliveryModal from "@/shared/components/ServiceDeliveryModal";
import FindingInspectModal from "@/shared/components/FindingInspectModal";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import {
    ArrowLeft, BadgeCheck, Building2, ClipboardList, Download, Globe, History, RotateCcw, ShieldAlert, Target, Users, CalendarCheck, CalendarClock,  Eye, Flag, Hourglass, Layers, MessageSquare, MoreHorizontal,
    UserPlus, UserRound, Wallet, XCircle, type LucideIcon,
} from "lucide-react";
import { StatusSteps } from "@/app/pentesting/engagement/detailParts";
import {
    assignPentester,
    cancelEngagement,
    claimEngagement,
    completeEngagementReview,
    downloadEvidence,
    getEngagementDetail,
    getEngagementFinding,
    listEngagementFindings,
    listEngagementRetests,
    listAuditActivity,
    listPentesters,
    reassignEngagement,
    rescheduleEngagement,
    returnEngagementFromReview,
    scheduleEngagement,
    updateEngagementScoping,
    getEngagementReport,
    downloadReport,
} from "@/lib/serviceDeliveryService";
import type {
    Activity,
    EngagementActionResponse,
    EngagementDetail,
    EngagementStatus,
    FindingDetail,
    FindingListItem,
    PentesterListItem,
    ReportResponse,
    Retest,
} from "@/lib/serviceDeliveryTypes";
import {
    assessmentTypeLabels,
    controlFieldClass,
    displayName,
    downloadBlob,
    downloadTextFile,
    formatCurrency,
    formatDate,
    formatDateRange,
    formatDateTime,
    formatLabel,
    retestStatusPillClass,
    statusLabels,
    statusPillClass,
    whiteOutlineButtonClass,
} from "@/lib/serviceDeliveryUi";

const STATE_DESCRIPTIONS: Record<EngagementStatus, string> = {
    requested: "New request awaiting Service Delivery ownership. Claiming it moves the engagement into Scoping.",
    scoping: "Commercial and delivery details are being confirmed. Scope, final quote, pentester, and dates can still be changed.",
    scheduled: "Scope and commercial details are locked. Schedule and pentester changes are exceptional and require a reason.",
    in_progress: "Testing has started. Scope, quote, pentester, and schedule are locked; Service Delivery coordinates and monitors only.",
    review: "Pentester has submitted the engagement. Delivery configuration is locked while Service Delivery performs final quality review.",
    completed:"Engagment is complete and read-only. ",
    retesting: "Client has requested a retest on one or more findings. Read-only until all open retests resolve.",
    cancelled: "Engagement was cancelled and is read-only",
};

const SERVERITY_ORDER: Record<FindingListItem["severity"], number> = { critical:0, high:1, medium:2 ,low: 3, info:4};

const ACTION_TITLES: Record<Exclude<ActionKind, null>, string> = {
    editScope: "Edit Scope & Commercials",
    assign: "Assign Pentester",
    reassign: "Reassign Pentester",
    schedule: "Confirm Schedule",
    changeSchedule: "Change Scheduled Dates",
    cancel: "Cancel Engagement",
    return: "Return to Pentester",
};

type ActionKind = "editScope" | "assign" | "reassign" | "schedule" | "changeSchedule" | "cancel" | "return" | null;

export default function EngagementDetailPage() {
    const params = useParams<{ id: string}>();
    const [engagement, setEngagement] = useState< EngagementDetail | null>(null);
    const [pentesters, setPentesters] = useState<PentesterListItem[]>([]);
    const [findingsPreview, setFindingsPreview] = useState<FindingListItem[]>([]);
    const [retests, setRetests] = useState<Retest[]>([]);
    const [activity, setActivity] = useState<Activity[]>([]);
    const [report, setReport] = useState<ReportResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);
     const [isDownloadingReport, setIsDownloadingReport] = useState(false);
    const [activeAction, setActiveAction] =useState<ActionKind>(null);
    const [inspectFinding,setInspectFinding] = useState < FindingDetail | null> (null);
    

    const [scopeDraft, setScopeDraft] = useState("");
    const [quoteDraft, setQuoteDraft] = useState("");
    const [selectedPentesterId , setSelectedPentesterId] = useState("");
    const [reasonDraft,setReasonDraft] = useState("");
    const [startDraft ,setStartDraft] = useState("");
    const [endDraft, setEndDraft] = useState("");

    const [toast, setToast] = useState<{message: string; type: "success" | "error"} | null>(null);

    const load = useCallback(() => {
        setIsLoading(true);
        getEngagementDetail(params.id)
            .then(async (detail) =>{
                setEngagement(detail);
                const showFindings = ["in_progress", "review", "completed"].includes(detail.status);
                const showReport = ["review", "completed"].includes(detail.status);
                const [findings, retestList , activityRes, reportRes] = await Promise.all([
                    showFindings? listEngagementFindings(params.id, { limit: 100 }) : Promise.resolve({ items: [] ,pagination: { total:0 , limit:0 , offset: 0, has_more: false}}),
                    detail.status === "completed" ? listEngagementRetests(params.id) :  Promise.resolve({ items: [] }),
                    listAuditActivity({ limit:200}),
                    showReport ? getEngagementReport(params.id).catch(() => null) : Promise.resolve(null), 
                ]);
                setFindingsPreview(findings.items);
                setRetests(retestList.items);
                setActivity(activityRes.items.filter((a) => a.entity_id === params.id));
                setReport(reportRes);
            })
            .catch(console.error)
            .finally(()=> setIsLoading(false));
    }, [params.id]);

    useEffect( ()=> {
        load();
         listPentesters({ is_active: true }).then((res) => setPentesters(res.items)).catch(console.error);

    },[load]);

    if(isLoading || !engagement) {
        return(
            <>
                <ServiceDeliveryPageTitle  title=" Engagement" />
                <p className="mt-6 text-sm text-brand-text/70">Loading engagement...</p>
            </>

        );

    }

    const availableForAssessment = pentesters.filter((p) => p.specialisations.includes(engagement.assessment_type));

function closeAction() {
        setActiveAction(null);
        setScopeDraft("");
        setQuoteDraft("");
        setSelectedPentesterId("");
        setReasonDraft("");
        setStartDraft("");
        setEndDraft("");
}

function notify(message: string, type: "success" | "error" = "success") {
    setToast({message, type});
    setTimeout(() => setToast(null), 2500);
}

async function runAndReload(action: Promise<EngagementActionResponse | null>) { 
    try {
        await action;
        load();
        closeAction();
        notify("Action completed successfully.");
    } catch (err) {
        console.error(err);
        notify(err instanceof Error ? err.message: "Action failed.", "error");
    }
}

    const overview: { label: string; value: string; icon: LucideIcon; color: string }[] = [
        { label: "Client", value: displayName(engagement.client), icon: Building2, color: "#2bd8f5" },
        { label: "Assessment type", value: assessmentTypeLabels[engagement.assessment_type], icon: Layers, color: "#facc15" },
        { label: "Engagement type", value: formatLabel(engagement.engagement_type), icon: Eye, color: "#a78bfa" },
        { label: "Priority", value: formatLabel(engagement.priority), icon: Flag, color: engagement.priority === "high" ? "#ef4444" : engagement.priority === "medium" ? "#facc15" : "#4ade80" },
        { label: "Requested dates", value: formatDateRange(engagement.requested_start_date, engagement.requested_end_date), icon: CalendarClock, color: "#94a3b8" },
        { label: "Scheduled dates", value: formatDateRange(engagement.scheduled_start_date, engagement.scheduled_end_date), icon: CalendarCheck, color: "#a855f7" },
        { label: "Estimated quote", value: formatCurrency(engagement.estimated_quote), icon: Wallet, color: "#4ade80" },
        { label: "Final quote", value: formatCurrency(engagement.final_quote), icon: BadgeCheck, color: "#4ade80" },
    ];
    const stageDates: Record<string, string | null> = {
        requested: engagement.created_at,
        scoping: engagement.reviewed_at ?? null,
        scheduled: engagement.scheduled_start_date ?? null,
        in_progress: engagement.started_at ?? null,
        completed: engagement.completed_at ?? null,
    };


    const showFindings = ["in_progress","review","completed"].includes(engagement.status);
    const showRetests = engagement.status === "completed";
    const showReport = ["review", "completed"].includes(engagement.status);
    
    const previewFindings = [...findingsPreview]
    .sort((a, b) => SERVERITY_ORDER[a.severity] - SERVERITY_ORDER[b.severity]);


    async function openFinding(findingId: string) {
        const detail = await getEngagementFinding(params.id , findingId);
        setInspectFinding(detail);
    }

    async function handleDownloadReport() {
        if (!report) return;
        setIsDownloadingReport(true);
        try {
            const blob = await downloadReport(report.report_id ?? report.id);
            downloadBlob(`engagement-report-v${report.version}.pdf`, blob);
        } catch {
        } finally {
            setIsDownloadingReport(false);
        }
    }

    

    async function downloadFindingEvidence(f: FindingListItem) {
        const detail = await getEngagementFinding(params.id, f.id);
        if (detail.evidence_files && detail.evidence_files.length > 0) {
            const firstFile = detail.evidence_files.find(
                (file) => file.quarantine_status === "clean",
            );

            if (detail.evidence_files.length > 0 && !firstFile) {
                window.alert(
                    "No attachment has passed its security check yet. " +
                    "Open Inspect to view attachment status.",
                );
                return;
            }
            if (firstFile) {
                const blob = await downloadEvidence(firstFile.id, firstFile.file_name);
                downloadBlob(firstFile.file_name, blob);
                return;
            }
        }
        downloadTextFile(
            `${f.title.replace(/\s+/g, "-").toLowerCase()}.txt`,
            `PenFlow Finding\n\n${f.title}\nAsset: ${f.asset_identifier ?? "-"}
            \nSeverity: ${formatLabel(f.severity)}\nStatus: ${formatLabel(f.status)}
            \n\nNo evidence file is attached to this finding.`,
        );
    }

    return (
    <>
        <ServiceDeliveryPageTitle title={engagement.title}/>
        <div className="mt-4 flex items-center justify-between gap-4">
            <Link href="/service-delivery/engagements" className="inline-flex items-center gap-1.5 text-sm text-brand-cyan no-underline hover:underline">
                <ArrowLeft className="size-4" /> Back to Engagements
            </Link>
            <span className={cn("shrink-0 rounded-md border px-3 py-1 text-xs font-semibold", statusPillClass[engagement.status])}>
                {statusLabels[engagement.status].toUpperCase()}
            </span>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-brand-panel-border bg-brand-panel p-4">
            <div className="min-w-0">
                <b className="text-brand-text">{statusLabels[engagement.status]} workspace</b>
                <p className="mt-1 text-sm text-brand-text/70">{STATE_DESCRIPTIONS[engagement.status]}</p>
            </div>
            {engagement.status === "review" && (
                <div className="flex shrink-0 gap-2">
                    <Button variant="outline" size="sm" className="cursor-pointer border-white/70 bg-transparent text-white transition-colors hover:border-brand-cyan hover:bg-brand-cyan/10 hover:text-brand-cyan dark:border-white/70 dark:bg-transparent dark:hover:border-brand-cyan dark:hover:bg-brand-cyan/10" onClick={() => setActiveAction("return")}>Return to Pentester</Button>
                    <Button size="sm" className="cursor-pointer bg-brand-cyan text-[#04121f] transition-colors hover:bg-brand-cyan/80" onClick={() => runAndReload(completeEngagementReview(engagement.id))}>
                        Complete Engagement
                    </Button>
                </div>
            )}
        </div>

        <div className="mt-4">
            <StatusSteps status={engagement.status} stageDates={stageDates} />
        </div>

        <Card className="mt-4 border-brand-panel-border bg-brand-panel">
        <CardContent> 
            <div className="mb-3 flex items-start justify-between gap-3">
                <CardHeading icon={ClipboardList} color="#2bd8f5">Engagement Overview</CardHeading>
                <div className="flex flex-wrap gap-2">
                                {engagement.status === "requested" && (
                                <Button size="sm" className="cursor-pointer bg-brand-cyan text-[#04121f] transition-colors hover:bg-brand-cyan/80" onClick={() => runAndReload(claimEngagement(engagement.id))}>Claim Request</Button>
                            )}
                            {engagement.status === "scoping" && (
                                <Button size="sm" className="cursor-pointer bg-brand-cyan text-[#04121f] transition-colors hover:bg-brand-cyan/80" onClick={() => { setScopeDraft(engagement.scope); setQuoteDraft(engagement.final_quote ?? ""); setActiveAction("editScope"); }}>
                                    Edit Scope
                                </Button>
                            )}
                            {engagement.status === "scoping" && (
                                <Button size="sm" className="cursor-pointer bg-brand-success text-[#04121f] transition-colors hover:bg-brand-success/80" onClick={() => setActiveAction("schedule")}>Confirm</Button>
                            )}
                            {engagement.status === "scheduled" && (
                                <Button variant="outline" size="sm" className="cursor-pointer border-white/70 bg-transparent text-white transition-colors hover:border-brand-cyan hover:bg-brand-cyan/10 hover:text-brand-cyan dark:border-white/70 dark:bg-transparent dark:hover:border-brand-cyan dark:hover:bg-brand-cyan/10" onClick={() => setActiveAction("changeSchedule")}>Change Schedule</Button>
                            )}
                            {["requested", "scoping", "scheduled", "in_progress"].includes(engagement.status) && (
                                <MoreMenu onCancel={() => setActiveAction("cancel")} />
                            )}
                </div>
            </div>

            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                {overview.map(({ label, value, icon: Icon, color }) => (
                    <div key={label} className="rounded-md border border-brand-panel-border/75 bg-brand-panel-deep p-3">
                        <div className="mb-1 flex items-center gap-1.5 text-[10px] tracking-wide text-brand-text/70 uppercase">
                            <Icon aria-hidden="true" className="size-3.5" style={{ color }} />
                            {label}
                        </div>
                        <div className="text-sm font-semibold text-brand-text">{value}</div>
                    </div>
                ))}
            </div>

        </CardContent>
        </Card>

        <div className="mt-4 grid grid-cols-[minmax(0,1fr)_340px] items-start gap-4 max-lg:grid-cols-1">
            <div className="flex min-w-0 flex-col gap-4">
                <Card className="border-brand-panel-border bg-brand-panel">
                        <CardContent>
                            <CardHeading icon={Globe} color="#2bd8f5" className="mb-4">Declared Assets</CardHeading>
                            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                                {engagement.assets.map((a) => (
                                    <div key={a.id} className="flex items-center justify-between gap-3 rounded-md border border-brand-panel-border bg-brand-panel-deep p-3">
                                        <div>
                                            <div className="text-sm font-semibold text-brand-text">{a.identifier}</div>
                                            <div className="text-xs text-brand-text/70">{formatLabel(a.asset_type)}</div>
                                        </div>
                                        <span className="rounded-md border border-brand-success/40 bg-brand-success/10 px-2 py-0.5 text-[10px] font-semibold text-brand-success">
                                            IN SCOPE
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                <Card className="border-brand-panel-border bg-brand-panel">
                <CardContent>
                    {engagement.objective && (
                        <>
                            <CardHeading icon={Target} color="#facc15" className="mb-3">Objective</CardHeading>
                            <p className="rounded-md border border-brand-panel-border bg-brand-panel-deep p-3 text-sm text-brand-text/90">{engagement.objective}</p>
                        </>
                    )}
                    <CardHeading icon={Layers} color="#a78bfa" className="mt-5 mb-3">Scope && Constraints</CardHeading>
                    <p className="rounded-md border border-brand-panel-border bg-brand-panel-deep p-3 text-sm text-brand-text/90">{engagement.scope}</p>
                    {engagement.constraints && (
                        <p className="mt-2 rounded-md border border-brand-panel-border bg-brand-panel-deep p-3 text-sm text-brand-text/90">{engagement.constraints}</p>
                    )}
                </CardContent>
                </Card>
                 {showFindings && (
                    <Card className="border-brand-panel-border bg-brand-panel">
                        <CardContent>
                            <div className="mb-3 flex items-start justify-between gap-3">
                                <div>
                                    <CardHeading icon={ShieldAlert} color="#ef4444">Findings</CardHeading>
                                    <p className="text-xs text-brand-text/70">
                                        {engagement.finding_summary.total
                                            ? `${engagement.finding_summary.total} finding${engagement.finding_summary.total === 1 ? "" : "s"}, most severe first.`
                                            : "No findings have been submitted yet."}
                                    </p>
                                </div>
                                {showReport && (
                                    <button
                                        type="button"
                                        onClick={() => void handleDownloadReport()}
                                        disabled={report?.status !== "completed" || isDownloadingReport}
                                        title={
                                            !report ? "No report generated yet"
                                                : report.status === "failed" ? `Report generation failed${report.error_message ? `: ${report.error_message}` : ""}`
                                                : report.status !== "completed" ? `Report is ${formatLabel(report.status).toLowerCase()}`
                                                : report.generated_at ? `Version ${report.version} · generated ${formatDateTime(report.generated_at)}` : undefined
                                        }
                                        className={cn(
                                            "inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors disabled:cursor-not-allowed",
                                            report?.status === "completed"
                                                ? "bg-brand-cyan text-[#04121f] hover:bg-brand-cyan/85"
                                                : "bg-brand-panel-deep text-[#94a3b8] ring-1 ring-brand-panel-border ring-inset"
                                        )}
                                    >
                                        <Download className="size-3.5" />
                                        {isDownloadingReport ? "Downloading..." : report?.status === "completed" ? "Download report" : report?.status === "failed" ? "Report failed" : "Report not ready"}
                                        {report?.status === "completed" && !isDownloadingReport && <span className="text-[11px] font-normal opacity-70">PDF</span>}
                                    </button>
                                )}
                            </div>
                            {previewFindings.length === 0 ? (
                                <p className="text-sm text-brand-text/70">No findings have been submitted yet.</p>
                            ) : (
                                <ul className="m-0 grid list-none gap-2 p-0">
                                    {previewFindings.map((f) => (
                                        <li
                                            key={f.id}
                                            role="button"
                                            tabIndex={0}
                                            onClick={() => openFinding(f.id)}
                                            onKeyDown={(ev) => { if (ev.key === "Enter") openFinding(f.id); }}
                                            title="Open finding"
                                            className={cn("flex cursor-pointer items-center gap-4 rounded-xl border border-l-[3px] bg-brand-panel-deep/40 px-4 py-3.5 transition-colors hover:bg-white/[0.05]", FINDING_EDGE[f.severity])}
                                        >
                                            <div className="min-w-0 flex-1">
                                                <div className="truncate text-[15px] font-medium text-brand-text">{f.title}</div>
                                                <div className="truncate text-[11px] text-brand-text/60">{f.asset_identifier ?? "-"}</div>
                                            </div>
                                            <div className="flex shrink-0 flex-col items-end gap-1.5">
                                                <span className={cn("w-20 rounded-md border py-0.5 text-center text-[10px] font-bold uppercase", FINDING_PILL[f.severity])}>
                                                    {formatLabel(f.severity)}
                                                </span>
                                            </div>
                                            <div className="flex shrink-0 gap-1.5">
                                                <button
                                                    type="button"
                                                    onClick={(ev) => { ev.stopPropagation(); void downloadFindingEvidence(f); }}
                                                    className={ROW_ACTION}
                                                    title="Download evidence"
                                                    aria-label="Download evidence"
                                                >
                                                    <Download className="size-3.5" />
                                                </button>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </CardContent>
                    </Card>
                )}
            </div>
                <div className="flex min-w-0 flex-col gap-4">
                    <Card className="border-brand-panel-border bg-brand-panel">
                        <CardContent>
                            <CardHeading icon={Users} color="#2bd8f5" className="mb-4">People</CardHeading>
                            <dl className="m-0 grid grid-cols-1 gap-5">
                                <ContactRow role="Client" name={displayName(engagement.client)}>
                                    {engagement.status !== "requested" && (
                                        <Link href={`/service-delivery/messages?engagement=${engagement.id}&channel=client_service_delivery`} className={QUIET_LINK}>
                                            <MessageSquare className="size-3.5" /> Message client
                                        </Link>
                                    )}
                                </ContactRow>
                                <ContactRow
                                    role="Service Delivery"
                                    name={engagement.service_delivery ? displayName(engagement.service_delivery) : null}
                                    placeholder="Unclaimed"
                                />
                                <ContactRow
                                    role="Pentester"
                                    name={engagement.assigned_pentester ? displayName(engagement.assigned_pentester) : null}
                                    placeholder="Needs pentester"
                                    needsAction={!engagement.assigned_pentester && ["scoping", "scheduled"].includes(engagement.status)}
                                >
                                    {engagement.assigned_pentester && (
                                        <Link href={`/service-delivery/messages?engagement=${engagement.id}&channel=service_delivery_pentester`} className={QUIET_LINK}>
                                            <MessageSquare className="size-3.5" /> Message pentester
                                        </Link>
                                    )}
                                    {engagement.status === "scoping" && (
                                        <button type="button" onClick={() => setActiveAction("assign")} className={QUIET_LINK}>
                                            <UserPlus className="size-3.5" /> {engagement.assigned_pentester ? "Change pentester" : "Assign pentester"}
                                        </button>
                                    )}
                                    {engagement.status === "scheduled" && (
                                        <button type="button" onClick={() => setActiveAction("reassign")} className={QUIET_LINK}>
                                            <UserPlus className="size-3.5" /> Change pentester
                                        </button>
                                    )}
                                </ContactRow>
                            </dl>
                        </CardContent>
                    </Card>
                    <Card className="border-brand-panel-border bg-brand-panel">
                        <CardContent>
                            <CardHeading icon={History} color="#a78bfa" className="mb-4">Engagement Activity</CardHeading>
                            {activity.length === 0 ? (
                                <p className="text-sm text-brand-text/70">No recorded activity yet.</p>
                            ) : (
                                <div className="space-y-3">
                                    {activity.map((entry) => (
                                        <div key={entry.id} className="flex gap-3">
                                        
                                            <div>
                                                <p className="text-sm text-brand-text">
                                                    {displayName(entry.actor, "System")} · {formatLabel(entry.action)}
                                                </p>
                                                <p className="text-[11px] text-brand-text/70">{formatDateTime(entry.created_at)}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
        </div>



            {showRetests && (
                <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
                    {showRetests && (
                        <Card className="border-brand-panel-border bg-brand-panel">
                            <CardContent>
                                <CardHeading icon={RotateCcw} color="#2bd8f5" className="mb-4">Re-tests</CardHeading>
                                {retests.length === 0 ? (
                                    <p className="text-sm text-brand-text/70">No re-tests linked to this engagement.</p>
                                ) : (
                                    <div className="space-y-2">
                                        {retests.map((r) => (
                                            <div key={r.id} className="flex items-center justify-between gap-3 rounded-md border border-brand-panel-border bg-brand-panel-deep p-3">
                                                <div>
                                                    <div className="text-sm font-semibold text-brand-text">{r.finding.title}</div>
                                                    <div className="text-[11px] text-brand-text/70">Requested {formatDate(r.requested_at)}</div>
                                                </div>
                                                <span className={cn("rounded-md border px-2 py-0.5 text-[10px] font-semibold", retestStatusPillClass[r.status])}>
                                                    {formatLabel(r.status)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    )}

                </div>
            )}




            {activeAction && (
                <ServiceDeliveryModal title={ACTION_TITLES[activeAction]} onClose={closeAction}>
                    <ActionFormBody
                        kind={activeAction}
                        engagement={engagement}
                        availablePentesters={availableForAssessment}
                        scopeDraft={scopeDraft}
                        setScopeDraft={setScopeDraft}
                        quoteDraft={quoteDraft}
                        setQuoteDraft={setQuoteDraft}
                        selectedPentesterId={selectedPentesterId}
                        setSelectedPentesterId={setSelectedPentesterId}
                        reasonDraft={reasonDraft}
                        setReasonDraft={setReasonDraft}
                        startDraft={startDraft}
                        setStartDraft={setStartDraft}
                        endDraft={endDraft}
                        setEndDraft={setEndDraft}
                        onCancel={closeAction}
                        onSubmit={(action) => runAndReload(action)}
                    />
                </ServiceDeliveryModal>
            )}

            {inspectFinding && (
                <FindingInspectModal finding={inspectFinding} onClose={() => setInspectFinding(null)} />
            )}

            
        {toast && ( 
            <div className={cn(
                "fixed bottom-7 left-1/2 z-[90] -translate-x-1/2 rounded-lg border px-4 py-2.5 text-xs shadow-lg",
                toast.type === "success" ? "border-brand-cyan/40 bg-brand-deep text-foreground" : "border-red-500/40 bg-red-950/80 text-red-200"
            )}
        >
            {toast.message}
        </div>
    )}
    </>    
    )

}

function ActionFormBody({
    kind,
    engagement,
    availablePentesters,
    scopeDraft,
    setScopeDraft,
    quoteDraft,
    setQuoteDraft,
    selectedPentesterId,
    setSelectedPentesterId,
    reasonDraft,
    setReasonDraft,
    startDraft,
    setStartDraft,
    endDraft,
    setEndDraft,
    onCancel,
    onSubmit,
}: {
    kind: Exclude<ActionKind, null>;
    engagement: EngagementDetail;
    availablePentesters: PentesterListItem[];
    scopeDraft: string;
    setScopeDraft: (v: string) => void;
    quoteDraft: string;
    setQuoteDraft: (v: string) => void;
    selectedPentesterId: string;
    setSelectedPentesterId: (v: string) => void;
    reasonDraft: string;
    setReasonDraft: (v: string) => void;
    startDraft: string;
    setStartDraft: (v: string) => void;
    endDraft: string;
    setEndDraft: (v: string) => void;
    onCancel: () => void;
    onSubmit: (action: Promise<EngagementActionResponse | null>) => void;
}) {
    if (kind === "editScope") {
        return (
            <div className="mt-4 space-y-3">
                <div>
                    <label className="text-xs text-brand-text/70">Confirmed scope</label>
                    <textarea
                        value={scopeDraft}
                        onChange={(e) => setScopeDraft(e.target.value)}
                        className="mt-1 h-24 w-full rounded-md border border-brand-panel-border bg-brand-panel-deep p-2 text-sm text-brand-text outline-none"
                    />
                </div>
                <div>
                    <label className="text-xs text-brand-text/70">Final quote (ZAR)</label>
                    <Input value={quoteDraft} onChange={(e) => setQuoteDraft(e.target.value)} className={cn("mt-1", controlFieldClass)} />
                </div>
                <FormActions
                    onCancel={onCancel}
                    onSubmit={() => onSubmit(updateEngagementScoping(engagement.id, { scope: scopeDraft, final_quote: quoteDraft || null }))}
                    label="Save Changes"
                />
            </div>
        );
    }

    if (kind === "assign" || kind === "reassign") {
        const exception = kind === "reassign";
        return (
            <div className="mt-4 space-y-3">
                <p className="text-sm text-brand-text/70">
                    {exception
                        ? "This engagement is already scheduled. Reassignment requires an operational reason and will be audited."
                        : "Only specialists matching the assessment type are shown."}
                </p>
                <div>
                    <label className="text-xs text-brand-text/70">Pentester</label>
                    <Select value={selectedPentesterId} onValueChange={setSelectedPentesterId}>
                        <SelectTrigger className={cn("mt-1", controlFieldClass)}><SelectValue placeholder="Select a pentester" /></SelectTrigger>
                        <SelectContent>
                            {availablePentesters.length === 0 ? (
                                <SelectItem value="none" disabled>No matching pentester available</SelectItem>
                            ) : (
                                availablePentesters.map((p) => (
                                    <SelectItem key={p.id} value={p.id}>
                                        {p.full_name ?? p.email} - {p.specialisations.map((s) => assessmentTypeLabels[s]).join(" / ")}
                                    </SelectItem>
                                ))
                            )}
                        </SelectContent>
                    </Select>
                </div>
                {exception && (
                    <div>
                        <label className="text-xs text-brand-text/70">Reason for reassignment</label>
                        <textarea
                            value={reasonDraft}
                            onChange={(e) => setReasonDraft(e.target.value)}
                            className="mt-1 h-16 w-full rounded-md border border-brand-panel-border bg-brand-panel-deep p-2 text-sm text-brand-text outline-none"
                            placeholder="Required operational reason..."
                        />
                    </div>
                )}
                <FormActions
                    onCancel={onCancel}
                    disabled={!selectedPentesterId || (exception && !reasonDraft.trim())}
                    onSubmit={() =>
                        onSubmit(
                            exception
                                ? reassignEngagement(engagement.id, { pentester_id: selectedPentesterId, reason: reasonDraft.trim() })
                                : assignPentester(engagement.id, { pentester_id: selectedPentesterId }),
                        )
                    }
                    label={exception ? "Confirm Reassignment" : "Assign Pentester"}
                />
            </div>
        );
    }

    if (kind === "schedule" || kind ==="changeSchedule") {
        const exception = kind === "changeSchedule";
        const disabled = !exception && (!engagement.assigned_pentester || !engagement.final_quote);
        return (
            <div className="mt-4 space-y-3">
                {disabled && <p className="text-sm text-brand-alert">Assign a pentester and confirm the final quote before scheduling.</p>}
                <div className="grid grid-cols-2 gap-3">
                    <div>
                        <label className="text-xs text-brand-text/70">Start date</label>
                        <Input type="date" value={startDraft} onChange={(e) => setStartDraft(e.target.value)} className={cn("mt-1", controlFieldClass)} />
                    </div>
                    <div>
                        <label className="text-xs text-brand-text/70">End date</label>
                        <Input type="date" value={endDraft} onChange={(e) => setEndDraft(e.target.value)} className={cn("mt-1", controlFieldClass)} />
                    </div>
                </div>
                {exception && (
                    <div>
                        <label className="text-xs text-brand-text/70">Reason</label>
                        <textarea
                            value={reasonDraft}
                            onChange={(e) => setReasonDraft(e.target.value)}
                            className="mt-1 h-16 w-full rounded-md border border-brand-panel-border bg-brand-panel-deep p-2 text-sm text-brand-text outline-none"
                            placeholder="Required reason..."
                        />
                    </div>
                )}
                <FormActions
                    onCancel={onCancel}
                    disabled={disabled || !startDraft || !endDraft || (exception && !reasonDraft.trim())}
                    onSubmit={() =>
                        onSubmit(
                            exception
                                ? rescheduleEngagement(engagement.id, { scheduled_start_date: startDraft, scheduled_end_date: endDraft, reason: reasonDraft.trim() })
                                : scheduleEngagement(engagement.id, { scheduled_start_date: startDraft, scheduled_end_date: endDraft }),
                        )
                    }
                    label={exception ? "Confirm Change" : "Confirm && Schedule"}
                />
            </div>
        );
    }

    if (kind === "cancel") {
        return (
            <div className="mt-4 space-y-3">
                <p className="text-sm text-brand-text/70">Cancellation is permanent for this prototype and will be recorded in the audit trail.</p>
                <div>
                    <label className="text-xs text-brand-text/70">Reason</label>
                    <textarea
                        value={reasonDraft}
                        onChange={(e) => setReasonDraft(e.target.value)}
                        className="mt-1 h-16 w-full rounded-md border border-brand-panel-border bg-brand-panel-deep p-2 text-sm text-brand-text outline-none"
                    />
                </div>
                <FormActions
                    onCancel={onCancel}
                    disabled={!reasonDraft.trim()}
                    onSubmit={() => onSubmit(cancelEngagement(engagement.id, { reason: reasonDraft.trim() }))}
                    label="Cancel Engagement"
                    destructive
                    cancelLabel="Keep Engagement"
                />
            </div>
        );
    }

    return (
        <div className="mt-4 space-y-3">
            <p className="text-sm text-brand-text/70">Returning the engagement reopens testing.</p>
            <div>
                <label className="text-xs text-brand-text/70">Requested changes</label>
                <textarea
                    value={reasonDraft}
                    onChange={(e) => setReasonDraft(e.target.value)}
                    className="mt-1 h-20 w-full rounded-md border border-brand-panel-border bg-brand-panel-deep p-2 text-sm text-brand-text outline-none"
                    placeholder="Required review note..."
                />
            </div>
            <FormActions
                onCancel={onCancel}
                disabled={!reasonDraft.trim()}
                onSubmit={() => onSubmit(returnEngagementFromReview(engagement.id, { review_note: reasonDraft.trim() }))}
                label="Return Engagement"
            />
        </div>
    );
}

function FormActions({
    onCancel,
    onSubmit,
    label,
    disabled,
    destructive,
    cancelLabel = "Cancel",
}: {
    onCancel: () => void;
    onSubmit: () => void;
    label: string;
    disabled?: boolean;
    destructive?: boolean;
    cancelLabel?: string;
}) {
    return (
        <div className="flex justify-end gap-2">
        <Button variant="outline" size="sm" className={whiteOutlineButtonClass} onClick={onCancel}>{cancelLabel}</Button>
        <Button variant={destructive ? "destructive":"default"} size="sm" disabled={disabled} onClick={onSubmit}>
            {label}
        </Button>
        </div>
    );
}


const QUIET_LINK = "inline-flex items-center gap-1.5 rounded-md border border-brand-panel-border px-2.5 py-1 text-xs text-[#cbd5e1] no-underline transition-colors hover:border-brand-cyan/50 hover:text-brand-cyan";

function ContactRow({ role, name, placeholder = "—", needsAction = false, children }: {
    role: string; name: string | null; placeholder?: string; needsAction?: boolean; children?: React.ReactNode;
}) {
    return (
        <div className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-3">
            <span aria-hidden="true" className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-full bg-white/[0.06] text-[#94a3b8]">
                <UserRound className="size-4" />
            </span>
            <div className="min-w-0">
                <dt className="text-[11px] tracking-wide text-[#94a3b8] uppercase">{role}</dt>
                <dd className="m-0">
                    {name ? (
                        <span className="block truncate text-sm font-medium text-brand-text">{name}</span>
                    ) : needsAction ? (
                        <span className="mt-0.5 inline-flex items-center gap-1 rounded-full border border-dashed border-brand-orange/60 px-2 py-px text-[11px] text-brand-orange">
                            <Hourglass className="size-3" /> {placeholder}
                        </span>
                    ) : (
                        <span className="block text-sm text-brand-text/60 italic">{placeholder}</span>
                    )}
                    {children && <div className="mt-2 flex flex-wrap gap-2">{children}</div>}
                </dd>
            </div>
        </div>
    );
}

function MoreMenu({ onCancel }: { onCancel: () => void }) {
    const [open, setOpen] = useState(false);
    return (
        <div className="relative" onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setOpen(false); }}>
            <button
                type="button"
                onClick={() => setOpen((prev) => !prev)}
                aria-haspopup="menu"
                aria-expanded={open}
                aria-label="More actions"
                className="grid size-8 cursor-pointer place-items-center rounded-lg border border-brand-panel-border text-brand-text/70 transition-colors hover:border-brand-cyan/50 hover:bg-white/5 hover:text-brand-text"
            >
                <MoreHorizontal className="size-4" />
            </button>
            {open && (
                <div role="menu" className="absolute top-full right-0 z-30 mt-1.5 w-48 rounded-lg border border-brand-panel-border bg-[#0b1625] p-1.5 shadow-[0_12px_32px_rgba(0,0,0,0.6)]">
                    <button
                        type="button"
                        role="menuitem"
                        onClick={() => { setOpen(false); onCancel(); }}
                        className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-brand-alert hover:bg-brand-alert/10"
                    >
                        <XCircle className="size-4" /> Cancel engagement
                    </button>
                </div>
            )}
        </div>
    );
}


const FINDING_EDGE: Record<string, string> = {
    critical: "border-[#ef4444]/45 border-l-[#ef4444]",
    high: "border-[#f97316]/45 border-l-[#f97316]",
    medium: "border-[#facc15]/45 border-l-[#facc15]",
    low: "border-[#3b82f6]/45 border-l-[#3b82f6]",
    info: "border-[#64748b]/45 border-l-[#64748b]",
};
const FINDING_PILL: Record<string, string> = {
    critical: "border-[#ef4444]/60 bg-[#ef4444]/10 text-[#f87171]",
    high: "border-[#f97316]/60 bg-[#f97316]/10 text-[#fb923c]",
    medium: "border-[#facc15]/60 bg-[#facc15]/10 text-[#facc15]",
    low: "border-[#3b82f6]/60 bg-[#3b82f6]/10 text-[#60a5fa]",
    info: "border-[#64748b]/60 bg-[#64748b]/10 text-[#94a3b8]",
};
const ROW_ACTION = "inline-flex items-center gap-1.5 rounded-md border border-brand-panel-border p-1.5 text-xs text-[#cbd5e1] transition-colors hover:border-brand-cyan/50 hover:text-brand-cyan";


function CardHeading({ icon: Icon, color, children, className }: { icon: LucideIcon; color: string; children: React.ReactNode; className?: string }) {
    return (
        <h2 className={cn("m-0 flex items-center gap-3 text-lg font-semibold text-brand-text [font-family:inherit]! tracking-normal!", className)}>
            <span className="grid size-9 shrink-0 place-items-center rounded-lg" style={{ color, backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)` }}>
                <Icon className="size-5" />
            </span>
            {children}
        </h2>
    );
}