"use client";

import {  useEffect, useState } from "react";
import Link from "next/link";

import ServiceDeliveryPageTitle from "@/shared/components/ServiceDeliveryPageTitle";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getDashboard, listAuditActivity, listPentesters } from "@/lib/serviceDeliveryService";
import type { Activity, DashboardCounts, DashboardEngagementItem, DashboardResponse, EngagementStatus, PentesterListItem } from "@/lib/serviceDeliveryTypes";
import { availabilityDotClass, displayName, formatDateTime, formatLabel, statusDotClass, statusLabels, statusPillClass, whiteOutlineButtonClass } from "@/lib/serviceDeliveryUi";

type DonutStatus = Exclude<keyof DashboardCounts, "needs_attention">;

const DONUT_STATUSES: DonutStatus[] = ["requested", "scoping", "scheduled", "in_progress", "review"];

const DONUT_COLOR: Record<DonutStatus, string> = {
    requested: "#ff4d57",
    scoping: "#ff9f1c",
    scheduled: "#20c6c7",
    in_progress: "#1687ff",
    review: "#a78bfa",
    completed: "#2ecc71",
    cancelled: "#94a3b8",
};

function buildDonutGradient(counts: DashboardCounts): string {
    const total = DONUT_STATUSES.reduce((sum, status) => sum + counts[status], 0) || 1;
    let cursor = 0;
    const segments = DONUT_STATUSES.map((status) => {
        const start = (cursor / total) * 100;
        cursor += counts[status];
        const end = (cursor / total) * 100;
        return `${DONUT_COLOR[status]} ${start}% ${end}%`;
    });
    return `conic-gradient(${segments.join(", ")})`;
}

interface AttentionRow {
    engagement: DashboardEngagementItem;
    reason: string;
}

export default function ServiceDeliveryDashboardPage() {
    const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
    const [pentesters, setPentesters] = useState<PentesterListItem[] | null>(null);
    const [activity, setActivity] = useState<Activity[] | null>(null);

    useEffect(() => {
        getDashboard().then(setDashboard).catch(console.error);
        listPentesters({ limit: 100 }).then((res) => setPentesters(res.items)).catch(console.error);
        listAuditActivity({ limit: 5 }).then((res) => setActivity(res.items)).catch(console.error);
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
    const totalActive = DONUT_STATUSES.reduce((sum, status) => sum + counts[status], 0);

    const attention: AttentionRow[] = [
        ...dashboard.unclaimed_requests.map((engagement) => ({ engagement, reason: "New request" })),
        ...dashboard.awaiting_review.map((engagement) => ({ engagement, reason: "Submitted for approval" })),
    ];

    const availabilityCounts = pentesters?.reduce<Record<string, number>>((acc, p) => {
        acc[p.availability_status] = (acc[p.availability_status] ?? 0) + 1;
        return acc;
    }, {});

    return (
        <>
            <ServiceDeliveryPageTitle title="Service Delivery Dashboard" />

            <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-5">
                <MetricCard label="New Requests" value={counts.requested} status="requested" hint="Requires triage" tone="danger" />
                <MetricCard label="In Scoping" value={counts.scoping} status="scoping" hint="Needs pentester selection" />
                <MetricCard label="Scheduled" value={counts.scheduled} status="scheduled" hint="Starting soon" />
                <MetricCard label="In Progress" value={counts.in_progress} status="in_progress" hint="Actively being tested" />
                <MetricCard label="Ready for Review" value={counts.review} status="review" hint="Requires approval" tone="action" />
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
                <Card className="border-brand-panel-border bg-brand-panel">
                    <CardContent>
                        <h2 className="mb-4 text-sm font-semibold text-brand-text">Engagements by Status</h2>
                        <div className="flex items-center gap-6">
                            <div
                                className="relative grid size-[140px] shrink-0 place-items-center rounded-full"
                                style={{ background: buildDonutGradient(counts) }}
                            >
                                <div className="grid size-[90px] place-items-center rounded-full bg-brand-panel text-center">
                                    <div>
                                        <div className="text-lg font-bold text-brand-text">{totalActive}</div>
                                        <div className="text-[10px] text-brand-text/70">Active</div>
                                    </div>
                                </div>
                            </div>
                            <div className="flex-1 space-y-2">
                                {DONUT_STATUSES.map((status) => (
                                    <Link
                                        key={status}
                                        href={`/service-delivery/engagements?status=${status}`}
                                        className="flex items-center justify-between text-sm text-brand-text/90 hover:text-brand-text"
                                    >
                                        <span className="flex items-center gap-2">
                                            <span className={cn("size-2 rounded-full", statusDotClass[status])} />
                                            {statusLabels[status]}
                                        </span>
                                        <b>{counts[status]}</b>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-brand-panel-border bg-brand-panel">
                    <CardContent>
                        <h2 className="mb-4 text-sm font-semibold text-brand-text">Service Delivery Queue</h2>
                        <div className="divide-y divide-brand-panel-border/70">
                            <QueueRow label="Unclaimed requests" value={dashboard.unclaimed_requests.length} href="/service-delivery/engagements?status=requested" />
                            <QueueRow label="Engagements to review" value={dashboard.awaiting_review.length} href="/service-delivery/engagements?status=review" />
                            <QueueRow label="Upcoming (scheduled)" value={dashboard.upcoming_engagements.length} href="/service-delivery/engagements?status=scheduled" />
                            <QueueRow label="Needs attention" value={counts.needs_attention} href="/service-delivery/engagements" danger />
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-brand-panel-border bg-brand-panel">
                    <CardContent>
                        <h2 className="mb-4 text-sm font-semibold text-brand-text">Pentester Availability</h2>
                        {!availabilityCounts ? (
                            <p className="text-sm text-brand-text/70">Loading...</p>
                        ) : Object.keys(availabilityCounts).length === 0 ? (
                            <p className="text-sm text-brand-text/70">No pentesters on file.</p>
                        ) : (
                            <div className="space-y-1">
                                {Object.entries(availabilityCounts)
                                    .sort(([a], [b]) => a.localeCompare(b))
                                    .map(([status, count]) => (
                                        <Link
                                            key={status}
                                            href={`/service-delivery/pentesters?availability=${status}`}
                                            className="flex items-center justify-between rounded-md px-1 py-1.5 text-sm text-brand-text/90 hover:bg-white/5"
                                        >
                                            <span className="flex items-center gap-2">
                                                <span className={cn("size-2 rounded-full", availabilityDotClass(status))} />
                                                {formatLabel(status)}
                                            </span>
                                            <b>{count}</b>
                                        </Link>
                                    ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>  
            <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-[1.25fr_1fr]">
               <Card className="border-brand-panel-border bg-brand-panel">
                    <CardContent>
                        <h2 className="mb-4 text-sm font-semibold text-brand-text">Engagements Requiring Attention</h2>
                        {attention.length === 0 ? (
                            <p className="text-sm text-brand-text/70">Nothing needs attention right now.</p>
                            ): (
                                <div className="overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                    <thead>
                                        <tr className="text-[11px] text-brand-text/70">
                                            <th  className="pb-2 font-medium">Engagement</th>
                                            <th  className="pb-2 font-medium">Client</th>
                                            <th  className="pb-2 font-medium">Status</th>
                                            <th  className="pb-2 font-medium">Reason</th>
                                            <th className="pb-2 font-medium" />
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {attention.map(({ engagement, reason }) => (
                                            <tr key={engagement.id} className="border-t border-brand-panel-border/65">
                                                <td className="py-2.5">{engagement.title}</td>
                                                <td className="py-2.5">{displayName(engagement.client)}</td>
                                                <td className="py-2.5">
                                                    <span className={cn("rounded-md border px-2 py-0.5 text-[10px] font-semibold",statusPillClass[engagement.status])}>
                                                        {statusLabels[engagement.status].toUpperCase()}
                                                    </span>     
                                                </td>
                                                <td className="py-2.5 text-brand-text/70">{reason}</td>
                                                <td className="py-2.5 text-right">
                                                    <Link href = {`/service-delivery/engagements/${engagement.id}`}>
                                                        <Button variant= "outline" size = "sm" className={whiteOutlineButtonClass}>Open</Button>
                                                    </Link>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>    
                            </div>
                        )}
                    </CardContent>
               </Card>
                    <Card className="border-brand-panel-border bg-brand-panel">
                        <CardContent>
                            <h2 className="mb-4 text-sm font-semibold text-brand-text">Recent Activity</h2>
                            {! activity ? (
                                <p className="text-sm text-brand-text/70">Loading...</p>
                            ) :  activity.length === 0?(
                                <p className="text-sm text-brand-text/70">No recent activity.</p>
                            ): (
                                <div className="space-y-1">
                                {activity.map((item) => {
                                    const inner = (
                                    <>
                                        <p className="text-[13px] text-brand-text">
                                            {displayName(item.actor, "System")} | {formatLabel(item.action)}
                                        </p>
                                        <p className="mt-1 text-[11px] text-brand-text/70">{formatLabel(item.entity_type)}</p>
                                    </>
                                    );
                                    const isEngagement = item.entity_type === "engagement" && item.entity_id;
                                    return isEngagement ?(
                                        <Link 
                                            key = {item.id}
                                            href={`/service-delivery/engagements/${item.entity_id}`}
                                            className="flex items-start justify-between gap-3 rounded-lg px-2 py-2 hover:bg-white/5"
                                        >
                                            <div>{inner}</div>
                                            <span className="shrink-0 text-[11px] text-brand-text/70">{formatDateTime(item.created_at)}</span>
                                        </Link>
                                    ) : (
                                        <div key = {item.id} className="flex items-start justify-between gap-3 rounded-lg px-2 py-2">
                                        <div>{inner}</div>
                                        <span className="shrink-0 text-[11px] text-brand-text/70">{formatDateTime(item.created_at)}</span> 
                                        </div>
                                    );
                                })}

                                </div>
                            ) 
                            }
                        </CardContent>
                    </Card>
            </div>      
        </>
    );
}

function MetricCard({
    label,
    value,
    status,
    hint,
    tone,
}: {
    label: string;
    value: number;
    status: EngagementStatus;
    hint: string;
    tone?: "danger" | "action";
}) {
    return (
        <Link href={`/service-delivery/engagements?status=${status}`}>
            <Card className="border-brand-panel-border bg-brand-panel transition-colors hover:border-brand-cyan/40">
                <CardContent>
                    <div className="text-xs text-brand-text/80">{label}</div>
                    <div className="mt-2 text-2xl font-bold text-brand-text">{value}</div>
                    <div className={cn("mt-1 text-xs", tone === "danger" ? "text-brand-alert" : tone === "action" ? "text-brand-cyan" : "text-brand-text/70")}>
                        {hint}
                    </div>
                </CardContent>
            </Card>
        </Link>
    );
}

function QueueRow({ label, value, href, danger }: { label: string; value: number; href: string; danger?: boolean }) {
    return (
        <Link href={href} className="flex items-center justify-between py-2.5 text-sm text-brand-text/90 hover:text-brand-text">
            <span>{label}</span>
            <strong className={danger ? "text-brand-alert" : ""}>{value}</strong>
        </Link>
    );
}
