"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AlarmClock, Braces, Building2, Eye, EyeOff, Scan, CalendarClock, ChevronDown, RotateCcw, CheckCircle2, ChevronRight, ClipboardList, Cloud, FileCheck2, Inbox, PlayCircle, Globe, Hourglass, MoreHorizontal, Network, Search, Smartphone, UserRound, type LucideIcon } from "lucide-react";

import ServiceDeliveryPageTitle from "@/shared/components/ServiceDeliveryPageTitle";
import { cn } from "@/lib/utils";
import { listEngagements } from "@/lib/serviceDeliveryService";
import type { AssessmentType, EngagementListItem, EngagementStatus } from "@/lib/serviceDeliveryTypes";
import { assessmentTypeLabels, displayName, formatDateRange, statusLabels } from "@/lib/serviceDeliveryUi";
import ProgressLine from "@/app/pentesting/engagement/ProgressLine";
import StatusPill from "@/app/pentesting/console/components/StatusPill";
import type { EngagementStatus as StageStatus } from "@/app/pentesting/console/types";

const STATUS_OPTIONS: EngagementStatus[] = ["requested", "scoping", "scheduled", "in_progress", "review", "completed", "retesting", "cancelled"];
const ASSESSMENT_OPTIONS: AssessmentType[] = ["web_application", "mobile_application", "api", "network", "cloud", "other"];

type AssignmentFilter = "all" | "assigned" | "unassigned";

const ASSESSMENT_ICON: Record<AssessmentType, { icon: LucideIcon; color: string }> = {
    web_application: { icon: Globe, color: "#2bd8f5" },
    mobile_application: { icon: Smartphone, color: "#a78bfa" },
    api: { icon: Braces, color: "#facc15" },
    network: { icon: Network, color: "#4ade80" },
    cloud: { icon: Cloud, color: "#60a5fa" },
    other: { icon: MoreHorizontal, color: "#f472b6" },
};

const ENGAGEMENT_TYPE_ICON: Record<string, LucideIcon> = { black_box: EyeOff, grey_box: Eye, white_box: Scan };

const FIELD = "h-9 rounded-lg border border-brand-panel-border bg-brand-panel-deep px-3 text-sm text-brand-text outline-none focus:border-brand-cyan";
const DAY = 86_400_000;

function daysUntil(value: string | null | undefined): number | null {
    if (!value) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const date = new Date(value);
    date.setHours(0, 0, 0, 0);
    return Math.round((date.getTime() - today.getTime()) / DAY);
}

function stageWindow(e: EngagementListItem): { start: string | null | undefined; end: string | null | undefined } {
    return e.status === "requested" || e.status === "scoping"
        ? { start: e.requested_start_date, end: e.requested_end_date }
        : { start: e.scheduled_start_date, end: e.scheduled_end_date };
}

function dueText(e: EngagementListItem): { text: string; tone: "overdue" | "soon" | "normal" } {
    const { start, end } = stageWindow(e);
    if (e.status === "completed" || e.status === "cancelled") return { text: statusLabels[e.status], tone: "normal" };
    if (e.status === "review") return { text: "Waiting for your review", tone: "soon" };
    const toStart = daysUntil(start);
    if (toStart !== null && toStart > 0 && (e.status === "requested" || e.status === "scoping" || e.status === "scheduled")) {
        return { text: `Starts in ${toStart} day${toStart === 1 ? "" : "s"}`, tone: toStart <= 3 ? "soon" : "normal" };
    }
    const toEnd = daysUntil(end);
    if (toEnd === null) return { text: "No dates yet", tone: "normal" };
    if (toEnd < 0) return { text: `Overdue by ${-toEnd} day${toEnd === -1 ? "" : "s"}`, tone: "overdue" };
    if (toEnd === 0) return { text: "Due today", tone: "soon" };
    return { text: `Due in ${toEnd} day${toEnd === 1 ? "" : "s"}`, tone: toEnd <= 2 ? "soon" : "normal" };
}

const SECTIONS: { key: string; title: string; tone: "attention" | "active" | "normal"; icon: LucideIcon; color?: string; match: (e: EngagementListItem) => boolean; collapsible?: boolean }[] = [
    { key: "review", title: "Review", tone: "attention", icon: FileCheck2, color: "#f97316", match: (e) => e.status === "review" },
    { key: "requested", title: "Requested", tone: "attention", icon: Inbox, color: "#94a3b8", match: (e) => e.status === "requested" && !e.service_delivery },
    { key: "scoping", title: "Scoping", tone: "normal", icon: ClipboardList, color: "#f472b6", match: (e) => e.status === "scoping" || (e.status === "requested" && !!e.service_delivery) },
    { key: "scheduled", title: "Scheduled", tone: "normal", icon: CalendarClock, color: "#a855f7", match: (e) => e.status === "scheduled" },
    { key: "retesting", title: "Retesting", tone: "active", icon: RotateCcw, color: "#2bd8f5", match: (e) => e.status === "retesting" },
    { key: "active", title: "In progress", tone: "active", icon: PlayCircle, color: "#facc15", match: (e) => e.status === "in_progress" },
    { key: "closed", title: "Completed", tone: "normal", icon: CheckCircle2, color: "#4ade80", match: (e) => e.status === "completed" || e.status === "cancelled", collapsible: true },
];

export default function ServiceDeliveryEngagementsPage() {
    return (
        <Suspense fallback={null}>
            <ServiceDeliveryEngagementsPageInner />
        </Suspense>
    );
}

function ServiceDeliveryEngagementsPageInner() {
    const searchParams = useSearchParams();
    const [engagements, setEngagements] = useState<EngagementListItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [status, setStatus] = useState<EngagementStatus | "all">((searchParams.get("status") as EngagementStatus) || "all");
    const [assessmentType, setAssessmentType] = useState<AssessmentType | "all">("all");
    const [assignment, setAssignment] = useState<AssignmentFilter>("all");

    useEffect(() => {
        setIsLoading(true);
        listEngagements({
            search: search || undefined,
            status: status === "all" ? undefined : status,
            assessment_type: assessmentType === "all" ? undefined : assessmentType,
            assigned: assignment === "all" ? undefined : assignment === "assigned",
            limit: 100,
        })
            .then((res) => setEngagements(res.items))
            .catch(console.error)
            .finally(() => setIsLoading(false));
    }, [search, status, assessmentType, assignment]);

    const filtersOn = search !== "" || status !== "all" || assessmentType !== "all" || assignment !== "all";
    function clearFilters() {
        setSearch("");
        setStatus("all");
        setAssessmentType("all");
        setAssignment("all");
    }

    const sections = useMemo(() => {
        const due = (e: EngagementListItem) => stageWindow(e).end ?? "9999";
        return SECTIONS
            .map((section) => ({ ...section, items: engagements.filter(section.match).sort((a, b) => due(a).localeCompare(due(b))) }))
            .filter((section) => section.items.length > 0);
    }, [engagements]);

    return (
        <>
            <ServiceDeliveryPageTitle title="Engagements" />
            <p className="mt-2 text-sm text-brand-text/80">
                Claim requests, coordinate scope and quote, assign specialists, schedule testing, and review delivery.
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-2.5">
                <label className={cn(FIELD, "flex min-w-[240px] flex-1 items-center gap-2")}>
                    <Search className="size-4 shrink-0 text-brand-text/50" />
                    <input
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Search engagements or clients..."
                        aria-label="Search engagements"
                        className="w-full border-0 bg-transparent text-sm outline-none placeholder:text-brand-text/50"
                    />
                </label>
                <select value={status} onChange={(e) => setStatus(e.target.value as EngagementStatus | "all")} aria-label="Filter by status" className={FIELD}>
                    <option value="all">Status: All</option>
                    {STATUS_OPTIONS.map((s) => <option key={s} value={s}>Status: {statusLabels[s]}</option>)}
                </select>
                <select value={assessmentType} onChange={(e) => setAssessmentType(e.target.value as AssessmentType | "all")} aria-label="Filter by assessment" className={FIELD}>
                    <option value="all">Assessment: All</option>
                    {ASSESSMENT_OPTIONS.map((a) => <option key={a} value={a}>Assessment: {assessmentTypeLabels[a]}</option>)}
                </select>
                <select value={assignment} onChange={(e) => setAssignment(e.target.value as AssignmentFilter)} aria-label="Filter by pentester assignment" className={FIELD}>
                    <option value="all">Pentester: All</option>
                    <option value="assigned">Pentester: Assigned</option>
                    <option value="unassigned">Pentester: Needs one</option>
                </select>
                {filtersOn && (
                    <span className="text-xs text-brand-text/60">
                        {engagements.length} shown ·{" "}
                        <button type="button" onClick={clearFilters} className="text-brand-cyan hover:underline">Clear filters</button>
                    </span>
                )}
            </div>

            <div className="mt-5 flex flex-col gap-2">
                {isLoading ? (
                    <div className="flex flex-col gap-2" aria-label="Loading engagements">
                        {[0, 1, 2].map((i) => <div key={i} className="h-[74px] animate-pulse rounded-xl border border-brand-panel-border bg-brand-panel" />)}
                    </div>
                ) : sections.length === 0 ? (
                    <p className="m-0 rounded-xl border border-dashed border-brand-panel-border bg-brand-panel py-6 text-center text-sm text-brand-text/70">
                        {filtersOn ? "No engagements match these filters." : "No engagements yet."}
                    </p>
                ) : (
                    sections.map((section) => (
                        <Section key={section.key} title={section.title} icon={section.icon} color={section.color ?? "#94a3b8"} items={section.items} defaultOpen={section.key === "review"} />
                    ))
                )}
            </div>
        </>
    );
}


function Section({ title, icon: Icon, color, items, defaultOpen }: { title: string; icon: LucideIcon; color: string; items: EngagementListItem[]; defaultOpen: boolean }) {
    const [open, setOpen] = useState(defaultOpen);
    const overdue = items.filter((e) => dueText(e).tone === "overdue").length;
    return (
        <section className="flex flex-col gap-2">
            <button
                type="button"
                onClick={() => setOpen((prev) => !prev)}
                aria-expanded={open}
                className="group/bar flex w-full max-w-[360px] cursor-pointer items-center gap-3 rounded-xl border border-l-[3px] border-brand-panel-border bg-brand-panel px-4 py-3.5 text-left transition-colors hover:border-[color:var(--section-color)] hover:bg-white/[0.03]"
                style={{ borderLeftColor: color, "--section-color": color } as React.CSSProperties}
            >
                <Icon aria-hidden="true" className="size-7 shrink-0" style={{ color }} />
                <h2 className="m-0 text-xl font-semibold text-brand-text transition-colors group-hover/bar:text-[color:var(--section-color)] [font-family:inherit]! tracking-normal!">{title}</h2>
                <span className="text-lg text-brand-text/60 transition-colors group-hover/bar:text-[color:var(--section-color)]">{items.length}</span>
                {overdue > 0 && (
                    <span className="ml-auto inline-flex items-center gap-1 text-base font-semibold text-brand-orange" title={`${overdue} overdue`} aria-label={`${overdue} overdue`}>
                        <AlarmClock aria-hidden="true" className="size-5" />
                        {overdue}
                    </span>
                )}
                <ChevronDown aria-hidden="true" className={cn(overdue > 0 ? "ml-2" : "ml-auto", "size-7 text-brand-text/60 transition-transform", open && "rotate-180")} />
            </button>
            {open && (
                <ul className="m-0 ml-auto flex w-[calc(100%-2.5rem)] list-none flex-col gap-2 p-0 max-md:w-full">
                    {items.map((e) => <EngagementRow key={e.id} engagement={e} />)}
                </ul>
            )}
        </section>
    );
}

function EngagementRow({ engagement: e }: { engagement: EngagementListItem }) {
    const router = useRouter();
    const href = `/service-delivery/engagements/${e.id}`;
    const type = ASSESSMENT_ICON[e.assessment_type];
    const EngagementTypeIcon = ENGAGEMENT_TYPE_ICON[e.engagement_type] ?? Eye;
    const due = dueText(e);
    const { start, end } = stageWindow(e);
    const needsPentester = !e.assigned_pentester && ["scoping", "scheduled", "in_progress", "retesting"].includes(e.status);
    const unclaimed = e.status === "requested" && !e.service_delivery;

    return (
        <li
            role="link"
            tabIndex={0}
            onClick={() => router.push(href)}
            onKeyDown={(ev) => { if (ev.key === "Enter") router.push(href); }}
            className={cn(
                "group grid cursor-pointer grid-cols-[minmax(0,1fr)_auto_11rem_11rem_auto] items-center gap-5 rounded-xl border border-brand-panel-border bg-brand-panel px-5 py-3.5 transition-colors hover:border-brand-cyan/30 hover:bg-[#101e30]",
                "max-[1250px]:grid-cols-[minmax(0,1fr)_8.5rem_11rem_auto] max-md:grid-cols-[minmax(0,1fr)_auto] max-md:gap-3 max-md:px-4",
                due.tone === "overdue" && "shadow-[inset_3px_0_0_var(--color-brand-orange)]"
            )}
        >
            <span className="min-w-0">
                <span className="flex items-center gap-2">
                    <Link href={href} onClick={(ev) => ev.stopPropagation()} className="truncate font-semibold text-white no-underline transition-colors group-hover:text-brand-cyan">{e.title}</Link>
                    {e.priority === "high" && (
                        <span className="shrink-0 rounded-[4px] border border-brand-alert/50 bg-brand-alert/10 px-1.5 py-px text-[9px] font-bold text-brand-alert uppercase">High</span>
                    )}
                </span>
                <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-brand-text/60">
                    <span className="inline-flex items-center gap-1">
                        <Building2 aria-hidden="true" className="size-3.5" />
                        {displayName(e.client)}
                    </span>
                    <span aria-hidden="true">·</span>
                    <span className="inline-flex items-center gap-1">
                        <type.icon aria-hidden="true" className="size-3.5" style={{ color: type.color }} />
                        {assessmentTypeLabels[e.assessment_type]}
                    </span>
                    <span aria-hidden="true">·</span>
                    <span className="inline-flex items-center gap-1 capitalize">
                        <EngagementTypeIcon aria-hidden="true" className="size-3.5" />
                        {e.engagement_type.replace("_", " ")}
                    </span>
                </span>
            </span>

            <span className="pt-4 max-[1250px]:hidden"><ProgressLine status={e.status as StageStatus} /></span>
            <span className="min-[1250px]:hidden max-md:hidden"><StatusPill status={e.status as StageStatus} /></span>

            <span className="min-w-0 text-xs max-md:hidden">
                {e.assigned_pentester ? (
                    <span className="inline-flex min-w-0 items-center gap-1.5 text-[#cbd5e1]">
                        <UserRound aria-hidden="true" className="size-3.5 shrink-0 text-brand-text/50" />
                        <span className="truncate">{displayName(e.assigned_pentester)}</span>
                    </span>
                ) : needsPentester ? (
                    <span className="inline-flex items-center gap-1 rounded-full border border-dashed border-brand-orange/60 px-2 py-px text-[11px] whitespace-nowrap text-brand-orange">
                        <Hourglass aria-hidden="true" className="size-3" /> Needs pentester
                    </span>
                ) : unclaimed ? (
                    <span className="inline-flex items-center gap-1 rounded-full border border-dashed border-[#475569] px-2 py-px text-[11px] whitespace-nowrap text-brand-text/60">
                        Unclaimed
                    </span>
                ) : (
                    <span className="text-brand-text/40">—</span>
                )}
            </span>

            <span
                className={cn("text-sm whitespace-nowrap max-md:text-xs", due.tone === "overdue" ? "font-semibold text-brand-orange" : due.tone === "soon" ? "text-brand-yellow" : "text-[#cbd5e1]")}
                title={start && end ? formatDateRange(start, end) : undefined}
            >
                {due.text}
            </span>

            <ChevronRight aria-hidden="true" className="size-4 text-brand-text/40 transition-colors group-hover:text-brand-cyan max-md:hidden" />
        </li>
    );
}