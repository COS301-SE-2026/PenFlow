"use client";

import {  useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
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
} from "@/lib/serviceDeliveryService";
import type {
    Activity,
    EngagementActionResponse,
    EngagementDetail,
    EngagementStatus,
    FindingDetail,
    FindingListItem,
    PentesterListItem,
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
    severityClass,
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
    const router = useRouter();
    const [engagement, setEngagement] = useState< EngagementDetail | null>(null);
    const [pentesters, setPentesters] = useState<PentesterListItem[]>([]);
    const [findingsPreview, setFindingsPreview] = useState<FindingListItem[]>([]);
    const [retests, setRetests] = useState<Retest[]>([]);
    const [activity, setActivity] = useState<Activity[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [activeAction, setActiveAction] =useState<ActionKind>(null);
    const [inspectFinding,setInspectFinding] = useState < FindingDetail | null> (null);
    const [isReportViewOpen,setIsReportViewOpen] = useState(false);

    const [scopeDraft, setScopeDraft] = useState("");
    const [quoteDraft, setQuoteDraft] = useState("");
    const [selectedPentesterId , setSelectedPentesterId] = useState("");
    const [reasonDraft,setReasonDraft] = useState("");
    const [startDraft ,setStartDraft] = useState("");
    const [endDraft, setEndDraft] = useState("");

    const load = () => {
        setIsLoading(true);
        getEngagementDetail(params.id)
            .then(async (detail) =>{
                setEngagement(detail);
                const showFindings = ["in_progress", "review", "completed"].includes(detail.status);
                const [findings, retestList , activityRes] = await Promise.all([
                    showFindings? listEngagementFindings(params.id, { limit: 100}): Promise.resolve({ items: [] ,pagination: { total:0 , limit:0 , offset: 0, has_more: false}}), 
                    detail.status === "completed" ? listEngagementRetests(params.id) :  Promise.resolve({ items: [] }),
                    listAuditActivity({ limit:200}),
                ]);
                setFindingsPreview(findings.items);
                setRetests(retestList.items);
                setActivity(activityRes.items.filter((a) => a.entity_id === params.id));

            })
            .catch(console.error)
            .finally(()=> setIsLoading(false));
    };

    useEffect( ()=> {
        load();
         listPentesters({ is_active: true }).then((res) => setPentesters(res.items)).catch(console.error);

    },[params.id]);

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

async function runAndReload(action: Promise<EngagementActionResponse | null>) {
    await action;
    load();
    closeAction();
}

const overview: [string, string][] = [
        ["Client", displayName(engagement.client)],
        ["Assessment type", assessmentTypeLabels[engagement.assessment_type]],
        ["Engagement type", formatLabel(engagement.engagement_type)],
        ["Priority", formatLabel(engagement.priority)],
        ["Requested dates", formatDateRange(engagement.requested_start_date, engagement.requested_end_date)],
        ["Scheduled dates", formatDateRange(engagement.scheduled_start_date, engagement.scheduled_end_date)],
        ["Estimated quote", formatCurrency(engagement.estimated_quote)],
        ["Final quote", formatCurrency(engagement.final_quote)],
    ];


    const showFindings = ["in_progress","review","completed"].includes(engagement.status);
    const showRetests = engagement.status === "completed";
    const showReport = ["review", "completed"].includes(engagement.status);
    const previewFindings = [...findingsPreview]
    .sort((a, b) => SERVERITY_ORDER[a.severity] - SERVERITY_ORDER[b.severity])
    .slice(0, 5);


    async function openFinding(findingId: string) {
        const detail = await getEngagementFinding(params.id , findingId);
        setInspectFinding(detail);
    }

    async function downloadFindingEvidence(f: FindingListItem) {
        const detail = await getEngagementFinding(params.id, f.id);
        const firstFile = detail.evidence_files[0];
        if (firstFile){
            const blob = await downloadEvidence(firstFile.id,firstFile.file_name);
            downloadBlob(firstFile.file_name, blob)
            return;
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
            <div className="flex items-center gap-2 text-xs text-brand-text/70">
            <link href= "/service-delivery/engagements" className="text-brand-cyan hover:underline">Engagements</link>
            <span>&gt;</span>
            <span>{engagement.title}</span>
            </div>
            <span className={cn("shrink-0 rounded-md border px-3 py-1 text-xs font-semibold", statusPillClass[engagement.status])}>
                {statusLabels[engagement.status].toUpperCase()}
            </span>
        </div>

        <div className="mt-4 rounded-lg border border-brand-panel-border bg-brand-panel p-4">
            <b className="text-brand-text">{statusLabels[engagement.status]} workspace</b>
            <p className="mt-1 text-sm text-brand-text/70">{STATE_DESCRIPTIONS[engagement.status]}</p>
        </div>

        <Card className="mt-4 border-brand-panel-border bg-brand-panel">
            <CardContent>
                <h2 className="mb-3 text-sm font-semibold text-brand-text">Coordination</h2>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                    <PartyCard kicker="Client" name={displayName(engagement.client)} meta={engagement.client.email ?? "-"}>

                    </PartyCard>
                </div>
            </CardContent>

        </Card>
    </>    
    )

    
}

// client info display in party cards
function PartyCard({ kicker, name, meta, children }: { kicker: string; name: string; meta: string; children?: React.ReactNode }) {
    return (
        <div className="rounded-md border border-brand-panel-border bg-brand-panel-deep p-3">
            <div className="mb-1 text-[10px] tracking-wide text-brand-text/70 uppercase">{kicker}</div>
            <div className="text-sm font-semibold text-brand-text">{name}</div>
            <div className="mb-2 text-xs text-brand-text/70">{meta}</div>
            {children}
        </div>
    );
}

//handles all workflow edit scope ,assign,schedule,cancle,return
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


