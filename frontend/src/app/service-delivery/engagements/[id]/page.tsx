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

}
