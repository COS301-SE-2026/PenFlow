"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, Braces, CalendarClock, Clock, Cloud, Globe, MoreHorizontal, Network, Smartphone, CheckCircle2, ClipboardList, FileCheck2, History, Hourglass, Inbox, UserRound, PauseCircle, PlayCircle, Users, type LucideIcon } from "lucide-react";

import ServiceDeliveryPageTitle from "@/shared/components/ServiceDeliveryPageTitle";
import { cn } from "@/lib/utils";
import { getDashboard, listAuditActivity, listPentesters } from "@/lib/serviceDeliveryService";
import { activityPhrase, relativeTime, SYSTEM_ACTIVITY } from "../activity";
import { loadWorkload, WORKLOAD_PARTS, workloadTotal, type Workload } from "../workload";
import type { Activity, DashboardCounts, DashboardEngagementItem, DashboardResponse, EngagementStatus, PentesterListItem } from "@/lib/serviceDeliveryTypes";
import { displayName, formatDateTime, formatLabel } from "@/lib/serviceDeliveryUi";
import { formatDateRange } from "@/lib/engagementFormat";
import { STATUS_STEPS } from "@/app/pentesting/engagement/statusSteps";

type DonutStatus = Exclude<keyof DashboardCounts, "needs_attention">;

const DONUT_COLOR: Record<DonutStatus, string> = {
    ...(Object.fromEntries(STATUS_STEPS.map((step) => [step.status, step.color])) as Record<string, string>),
    cancelled: "#94a3b8",
} as Record<DonutStatus, string>;

const STAGE_ICON: Record<string, LucideIcon> = {
    requested: Inbox,
    scoping: ClipboardList,
    scheduled: CalendarClock,
    in_progress: PlayCircle,
    review: FileCheck2,
};


export default function ServiceDeliveryDashboardPage() {
    const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
    const [pentesters, setPentesters] = useState<PentesterListItem[] | null>(null);
    const [activity, setActivity] = useState<Activity[] | null>(null);
    const [workload, setWorkload] = useState<Record<string, Workload> | null>(null);
    const [titles, setTitles] = useState<Record<string, string>>({});

    useEffect(() => {
        getDashboard().then(setDashboard).catch(console.error);
        listPentesters({ limit: 100 }).then((res) => setPentesters(res.items)).catch(console.error);
        listAuditActivity({ limit: 40 }).then((res) => setActivity(res.items)).catch(console.error);
        loadWorkload()
            .then(({ workload, titles }) => { setWorkload(workload); setTitles(titles); })
            .catch(() => setWorkload({}));
    }, []);

    if (!dashboard) {
        return (
            <>
                <ServiceDeliveryPageTitle title="Service Delivery Dashboard" />
                <p className="mt-6 text-sm text-brand-text/70">Loading dashboard...</p>
            </>
        );
    }

    const { counts } = dashboard;



    return (
        <>
            <ServiceDeliveryPageTitle title="Service Delivery Dashboard" />

            <div className="mt-6">
                <PipelineLine
                    stages={[
                        { status: "requested", label: "New Requests", count: counts.requested, action: true },
                        { status: "scoping", label: "In Scoping", count: counts.scoping },
                        { status: "scheduled", label: "Scheduled", count: counts.scheduled },
                        { status: "in_progress", label: "In Progress", count: counts.in_progress },
                        { status: "review", label: "Ready for Review", count: counts.review, action: true },
                    ]}
                />

            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_420px]">
                <AttentionCard
                    requests={dashboard.unclaimed_requests}
                    reviews={dashboard.awaiting_review}
                    total={counts.needs_attention}
                />

                <div className="flex min-w-0 flex-col gap-3">
                <PentesterAvailability pentesters={pentesters} workload={workload} />
                    <RecentActivity
                        activity={activity}
                        titles={{
                            ...titles,
                            ...Object.fromEntries([...dashboard.unclaimed_requests, ...dashboard.awaiting_review, ...dashboard.upcoming_engagements].map((e) => [e.id, e.title])),
                        }}
                    />
                </div>
            </div>      
        </>
    );
}

interface PipelineStage {
    status: EngagementStatus;
    label: string;
    count: number;
    action?: boolean;
}

function PipelineLine({ stages }: { stages: PipelineStage[] }) {
    return (
        <div className="rounded-[10px] border border-brand-panel-border bg-brand-panel px-6 pt-5 pb-4 max-sm:px-4">
            <ol className="m-0 flex list-none p-0 max-sm:flex-col max-sm:gap-4">
                {stages.map((stage, index) => {
                    const color = DONUT_COLOR[stage.status as DonutStatus] ?? "#94a3b8";
                    const Icon = STAGE_ICON[stage.status] ?? Inbox;
                    const empty = stage.count === 0;
                    return (
                        <li
                            key={stage.status}
                            className="relative flex flex-1 flex-col items-center text-center max-sm:flex-row max-sm:gap-3 max-sm:text-left"
                        >
                            {index > 0 && (
                                <span
                                    aria-hidden="true"
                                    className="absolute top-[50px] right-1/2 h-0.5 w-full max-sm:top-auto max-sm:right-auto max-sm:bottom-1/2 max-sm:left-[21px] max-sm:h-[calc(100%+1rem)] max-sm:w-0.5"
                                    style={{ backgroundColor: DONUT_COLOR[stages[index - 1].status as DonutStatus], opacity: 0.45 }}
                                />
                            )}
                            <span className="mb-2 block h-5 text-sm leading-5 font-semibold tracking-wide uppercase max-sm:hidden" style={{ color: empty ? "#64748b" : color }}>
                                {stage.label}
                            </span>
                            <Link
                                href={`/service-delivery/engagements?status=${stage.status}`}
                                aria-label={`${stage.label}: ${stage.count}. View these engagements`}
                                className="group/node relative z-10 grid size-11 shrink-0 cursor-pointer place-items-center rounded-full border-2 transition-transform duration-200 hover:scale-125"
                                style={
                                    empty
                                        ? { borderColor: "#475569", backgroundColor: "var(--color-brand-panel)", color: "#64748b" }
                                        : {
                                            borderColor: color,
                                            color,
                                            backgroundColor: `color-mix(in srgb, ${color} 18%, var(--color-brand-panel))`,
                                            boxShadow: stage.action ? `0 0 0 3px var(--color-brand-panel), 0 0 0 5px ${color}` : undefined,
                                        }
                                }
                            >
                                <Icon className="size-5 transition-transform duration-200 group-hover/node:scale-110" strokeWidth={1.9} />
                            </Link>
                            <span className="mt-2.5 flex flex-col items-center max-sm:mt-0 max-sm:items-start">
                                <strong className={cn("text-[26px] leading-none", empty ? "text-brand-text/40" : "text-brand-text")}>{stage.count}</strong>
                                <span className="mt-1 text-sm font-semibold tracking-wide uppercase sm:hidden" style={{ color: empty ? "#64748b" : color }}>
                                    {stage.label}
                                </span>
                            </span>

                        </li>
                    );
                })}
            </ol>
        </div>
    );
}

const AVAILABILITY: Record<string, { label: string; icon: LucideIcon; color: string; order: number }> = {
    available: { label: "Available", icon: CheckCircle2, color: "#4ade80", order: 0 },
    engaged: { label: "Engaged", icon: Hourglass, color: "#f97316", order: 1 },
    unavailable: { label: "Unavailable", icon: PauseCircle, color: "#94a3b8", order: 2 },
};

const MAX_SHOWN = 8;

function PentesterAvailability({ pentesters, workload }: { pentesters: PentesterListItem[] | null; workload: Record<string, Workload> | null }) {
    const active = (pentesters ?? []).filter((p) => p.is_active);
    const groups = Object.entries(
        active.reduce<Record<string, PentesterListItem[]>>((acc, p) => {
            (acc[p.availability_status] ??= []).push(p);
            return acc;
        }, {})
    )
        .map(([status, people]) => ({ status, people: [...people].sort((a, b) => a.assigned_engagements - b.assigned_engagements) }))
        .sort((a, b) => (AVAILABILITY[a.status]?.order ?? 9) - (AVAILABILITY[b.status]?.order ?? 9));
    const availableCount = active.filter((p) => p.availability_status === "available").length;
    const ordered = groups.flatMap((group) => group.people);

    return (
        <section className="rounded-[10px] border border-brand-panel-border bg-brand-panel px-5 py-4">
            <h2 className="m-0 mb-3 flex items-center gap-3 text-lg font-semibold text-brand-text [font-family:inherit]! tracking-normal!">
                <span className="grid size-9 place-items-center rounded-lg bg-brand-cyan/10 text-brand-cyan"><Users className="size-5" /></span>
                Pentesters
                {pentesters && <span className="text-sm font-normal text-brand-text/60">· {availableCount} of {active.length} available</span>}
            </h2>
            {!pentesters ? (
                <p className="m-0 text-sm text-brand-text/70">Loading...</p>
            ) : active.length === 0 ? (
                <p className="m-0 text-sm text-brand-text/70">No pentesters on file.</p>
            ) : (
                <div className="grid gap-3">
                    <ul className="m-0 grid list-none gap-1 p-0">
                        {ordered.slice(0, MAX_SHOWN).map((p) => (
                            <PentesterRow
                                key={p.id}
                                pentester={p}
                                workload={workload ? workload[p.id] ?? { testing: 0, scheduled: 0, review: 0 } : null}
                            />
                        ))}
                    </ul>
                    {ordered.length > MAX_SHOWN && (
                        <Link href="/service-delivery/pentesters" className="inline-block px-1.5 text-xs text-brand-cyan hover:underline">
                            +{ordered.length - MAX_SHOWN} more
                        </Link>
                    )}
                </div>
            )}
        </section>
    );
}

function PentesterRow({ pentester: p, workload }: { pentester: PentesterListItem; workload: Workload | null }) {
    const name = p.full_name ?? p.email;
    const status = AVAILABILITY[p.availability_status] ?? { label: formatLabel(p.availability_status), color: "#94a3b8" };
    const total = workloadTotal(workload ?? undefined);
    const breakdown = workload
        ? WORKLOAD_PARTS.filter((part) => workload[part.key] > 0).map((part) => `${workload[part.key]} ${part.label}`).join(" · ") || "No current engagements"
        : "Loading workload...";
    return (
        <li className="group/row relative">
            <Link
                href={`/service-delivery/pentesters?availability=${p.availability_status}`}
                aria-label={`${name}: ${breakdown}`}
                className="flex items-center gap-2.5 rounded-lg px-1.5 py-1.5 no-underline hover:bg-white/5"
            >
                <span aria-hidden="true" className="grid size-8 shrink-0 place-items-center rounded-full bg-white/[0.06] text-[#94a3b8]">
                    <UserRound className="size-4" />
                </span>
                <span className="min-w-0 flex-1 truncate text-sm text-brand-text">{name}</span>
            </Link>

            {workload && (
                <div
                    role="tooltip"
                    className="pointer-events-none invisible absolute top-full right-0 left-0 z-30 mt-1 rounded-lg border border-brand-panel-border bg-[#0b1625] p-3 opacity-0 shadow-[0_12px_32px_rgba(0,0,0,0.6)] transition-opacity group-hover/row:visible group-hover/row:opacity-100"
                >
                    <p className="m-0 flex items-start justify-between gap-2">
                        <span className="truncate text-sm font-semibold text-brand-text">{name}</span>
                        <span
                            className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase"
                            style={{ color: status.color, backgroundColor: `color-mix(in srgb, ${status.color} 14%, transparent)` }}
                        >
                            {status.label}
                        </span>
                    </p>
                    <p className="m-0 truncate text-[11px] text-brand-text/60">{p.email}</p>
                    <span className="mt-2.5 flex items-center justify-between text-xs font-semibold text-brand-text">
                        Assigned <span>{total}</span>
                    </span>
                    <span className="mt-1.5 grid gap-1 border-t border-brand-panel-border pt-1.5">
                        {WORKLOAD_PARTS.map((part) => (
                            <span key={part.key} className="flex items-center justify-between text-xs text-[#cbd5e1]">
                                <span className="inline-flex items-center gap-1.5">
                                    <span className="size-2 rounded-full" style={{ backgroundColor: DONUT_COLOR[part.status as DonutStatus] }} />
                                    {part.key === "testing" ? "Testing now" : part.key === "scheduled" ? "Scheduled" : "In review"}
                                </span>
                                <span className="font-semibold text-brand-text">{workload[part.key]}</span>
                            </span>
                        ))}
                    </span>
                </div>
            )}
        </li>
    );
}


function RecentActivity({ activity, titles }: { activity: Activity[] | null; titles: Record<string, string> }) {
    const items = (activity ?? []).filter((item) => !SYSTEM_ACTIVITY.test(item.action) && item.entity_type !== "http_request").slice(0, 6);
    return (
        <section className="rounded-[10px] border border-brand-panel-border bg-brand-panel px-5 py-4">
            <h2 className="m-0 mb-3 flex items-center gap-3 text-lg font-semibold text-brand-text [font-family:inherit]! tracking-normal!">
                <span className="grid size-9 place-items-center rounded-lg bg-[#a78bfa]/10 text-[#a78bfa]"><History className="size-5" /></span>
                Recent activity
            </h2>
            {!activity ? (
                <p className="m-0 text-sm text-brand-text/70">Loading...</p>
            ) : items.length === 0 ? (
                <p className="m-0 text-sm text-brand-text/70">No recent activity.</p>
            ) : (
                <ul className="m-0 grid list-none gap-0.5 p-0">
                    {items.map((item) => {
                        const kind = { phrase: activityPhrase(item.action) };
                        const engagementId = item.entity_type === "engagement" ? item.entity_id : null;
                        const title = engagementId ? titles[engagementId] : undefined;
                        const body = (
                            <>
                                <span className="min-w-0 flex-1">
                                    <span className="block text-[13px] leading-snug text-[#cbd5e1]">
                                        <strong className="font-semibold text-brand-text">{displayName(item.actor, "System")}</strong>{" "}
                                        {engagementId ? kind.phrase : kind.phrase.replace(/ (on|to)$/, "")}
                                        {engagementId && <> <strong className="font-semibold text-brand-text">{title ?? "an engagement"}</strong></>}
                                    </span>
                                </span>
                                <span
                                    className="inline-flex shrink-0 items-center gap-1 rounded-full border border-brand-panel-border bg-white/[0.03] px-2 py-0.5 text-[11px] whitespace-nowrap text-brand-text/70"
                                    title={formatDateTime(item.created_at)}
                                >
                                    <Clock className="size-3" />
                                    {relativeTime(item.created_at)}
                                </span>
                            </>
                        );
                        return (
                            <li key={item.id}>
                                {engagementId ? (
                                    <Link href={`/service-delivery/engagements/${engagementId}`} className="flex items-start gap-2.5 rounded-lg px-1.5 py-2 no-underline hover:bg-white/5">
                                        {body}
                                    </Link>
                                ) : (
                                    <div className="flex items-start gap-2.5 px-1.5 py-2">{body}</div>
                                )}
                            </li>
                        );
                    })}
                </ul>
            )}
        </section>
    );
}


const ASSESSMENT_ICON: Record<string, { icon: LucideIcon; label: string; color: string }> = {
    web_application: { icon: Globe, label: "Web application", color: "#2bd8f5" },
    mobile_application: { icon: Smartphone, label: "Mobile application", color: "#a78bfa" },
    api: { icon: Braces, label: "API", color: "#facc15" },
    network: { icon: Network, label: "Network", color: "#4ade80" },
    cloud: { icon: Cloud, label: "Cloud", color: "#60a5fa" },
    other: { icon: MoreHorizontal, label: "Other", color: "#f472b6" },
};

function waiting(value: string): { text: string; pill: string } {
    const hours = Math.floor((Date.now() - new Date(value).getTime()) / 3_600_000);
    const quiet = "border-brand-panel-border bg-white/[0.03] text-brand-text/70";
    if (Number.isNaN(hours)) return { text: "", pill: quiet };
    const days = Math.floor(hours / 24);
    const text = hours < 1 ? "Just now" : hours < 24 ? `${hours} h` : `${days} day${days === 1 ? "" : "s"}`;
    const pill = days >= 3 ? "border-brand-alert/50 bg-brand-alert/10 text-brand-alert"
        : days >= 1 ? "border-brand-yellow/50 bg-brand-yellow/10 text-brand-yellow"
        : quiet;
    return { text, pill };
}

const DETAIL_CHIP = "inline-flex items-center gap-1 rounded-[5px] border border-[#26364e] bg-[#091523] px-1.5 py-px text-[10px] text-[#9eacbd]";

function AttentionCard({ requests, reviews, total }: { requests: DashboardEngagementItem[]; reviews: DashboardEngagementItem[]; total: number }) {
    const oldestFirst = (a: DashboardEngagementItem, b: DashboardEngagementItem) => a.updated_at.localeCompare(b.updated_at);
    const shown = requests.length + reviews.length;
    const groups = [
        { key: "reviews", title: "Waiting for your review", items: [...reviews].sort(oldestFirst), action: "review" as const, color: DONUT_COLOR.review, icon: FileCheck2 },
        { key: "requests", title: "New requests", items: [...requests].sort(oldestFirst), action: "claim" as const, color: "#2bd8f5", icon: Inbox },
    ].filter((group) => group.items.length > 0);

    return (
        <section className="self-start rounded-[10px] border border-brand-panel-border bg-brand-panel px-5 py-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <h2 className="m-0 flex items-center gap-3 text-lg font-semibold text-brand-text [font-family:inherit]! tracking-normal!">
                    <span className="grid size-9 place-items-center rounded-lg bg-brand-alert/10 text-brand-alert"><AlertCircle className="size-5" /></span>
                    Requires attention
                    <span className="text-sm font-normal text-brand-text/60">· {total}</span>
                </h2>
                {shown < total && (
                    <Link href="/service-delivery/engagements" className="shrink-0 text-xs text-brand-cyan hover:underline">
                        Showing {shown} of {total} · View all
                    </Link>
                )}
            </div>
            {groups.length === 0 ? (
                <p className="m-0 text-sm text-brand-text/70">Nothing needs attention right now.</p>
            ) : (
                <div className="grid gap-5">
                    {groups.map((group) => (
                        <div key={group.key} className="min-w-0">
                            <p className="m-0 mb-1.5 flex items-center gap-1.5 px-1.5 text-[11px] font-semibold tracking-wide uppercase" style={{ color: group.color }}>
                                <group.icon className="size-3.5" />
                                {group.title} <span className="font-normal text-brand-text/60">· {group.items.length}</span>
                            </p>
                            <ul className="m-0 grid list-none gap-1.5 p-0">
                                {group.items.map((engagement) => (
                                    <AttentionRow key={engagement.id} engagement={engagement} action={group.action} color={group.color} />
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>
            )}
        </section>
    );
}

function AttentionRow({ engagement, action, color }: { engagement: DashboardEngagementItem; action: "claim" | "review"; color: string }) {
    const href = `/service-delivery/engagements/${engagement.id}`;
    const wait = waiting(engagement.updated_at);
    const type = ASSESSMENT_ICON[engagement.assessment_type];

    return (
        <li>
            <Link
                href={href}
                className="group flex items-center gap-3 rounded-lg border border-l-[3px] border-brand-panel-border bg-brand-panel-deep/40 px-3 py-2.5 no-underline transition-colors hover:bg-white/[0.04]"
                style={{ borderLeftColor: color }}
            >
                {type && (
                    <span
                        className="grid size-8 shrink-0 place-items-center rounded-lg"
                        style={{ color: type.color, backgroundColor: `color-mix(in srgb, ${type.color} 12%, transparent)` }}
                        title={type.label}
                    >
                        <type.icon className="size-4" />
                    </span>
                )}
                <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium text-brand-text group-hover:text-brand-cyan">{engagement.title}</span>
                        {engagement.priority === "high" && (
                            <span className="shrink-0 rounded-[4px] border border-brand-alert/50 bg-brand-alert/10 px-1.5 py-px text-[9px] font-bold text-brand-alert uppercase">High</span>
                        )}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-brand-text/60">{displayName(engagement.client)}</span>
                </span>
                <span className="flex shrink-0 flex-col items-end gap-1.5">
                    <span className={cn("inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] whitespace-nowrap", wait.pill)} title={`Waiting since ${formatDateTime(engagement.updated_at)}`}>
                        <Clock className="size-3" />
                        {wait.text}
                    </span>
                    <span className="flex flex-wrap items-center justify-end gap-1.5 text-xs text-brand-text/60">
                        {type && <span className={DETAIL_CHIP}><type.icon className="size-3" style={{ color: type.color }} />{type.label}</span>}
                        {action === "review" && engagement.assigned_pentester && (
                            <span className={DETAIL_CHIP}><UserRound className="size-3" />{displayName(engagement.assigned_pentester)}</span>
                        )}
                        {engagement.scheduled_start_date && (
                            <span className={DETAIL_CHIP}><CalendarClock className="size-3" />{formatDateRange(engagement.scheduled_start_date, engagement.scheduled_end_date ?? null)}</span>
                        )}
                    </span>
                </span>
            </Link>
        </li>
    );
}