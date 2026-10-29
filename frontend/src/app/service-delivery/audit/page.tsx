"use client"

import { Fragment, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronDown, Compass, Lock, MessageSquare, RotateCcw, Search, ShieldAlert, UserRound, Users, type LucideIcon } from "lucide-react";

import ServiceDeliveryPageTitle from "@/shared/components/ServiceDeliveryPageTitle";
import { cn } from "@/lib/utils";
import { listAuditActivity, listEngagements } from "@/lib/serviceDeliveryService";
import type { Activity } from "@/lib/serviceDeliveryTypes";
import { displayName, formatDateTime } from "@/lib/serviceDeliveryUi";
import { activityPhrase, relativeTime } from "../activity";

type Category = "engagement" | "finding" | "retest" | "message" | "security" | "users" | "other";

const CATEGORY: Record<Category, { label: string; icon: LucideIcon; color: string }> = {
    engagement: { label: "Engagement", icon: Compass, color: "#2bd8f5" },
    finding: { label: "Findings", icon: ShieldAlert, color: "#ef4444" },
    retest: { label: "Retests", icon: RotateCcw, color: "#a78bfa" },
    message: { label: "Messages", icon: MessageSquare, color: "#60a5fa" },
    security: { label: "Security", icon: Lock, color: "#f59e0b" },
    users: { label: "Users", icon: Users, color: "#4ade80" },
    other: { label: "Other", icon: UserRound, color: "#94a3b8" },
};
const FILTERS: ("all" | Category)[] = ["all", "engagement", "finding", "retest", "message", "security", "users"];

function categoryOf(log: Activity): Category {
    if (log.action.includes("comment") || log.entity_type === "engagement_comment") return "message";
    if (log.entity_type === "http_request" || log.action.startsWith("sensitive_request") || log.action.startsWith("auth.")) return "security";
    if (log.action.startsWith("finding.")) return "finding";
    if (log.action.startsWith("retest.")) return "retest";
    if (log.action.startsWith("pentester.") || log.action.startsWith("user.") || log.entity_type === "user") return "users";
    if (log.action.startsWith("engagement.")) return "engagement";
    return "other";
}

function dayLabel(value: string): string {
    const date = new Date(value);
    const today = new Date();
    const startOf = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
    const diff = Math.round((startOf(today) - startOf(date)) / 86_400_000);
    if (diff === 0) return "Today";
    if (diff === 1) return "Yesterday";
    return date.toLocaleDateString("en-ZA", { day: "numeric", month: "short", year: date.getFullYear() === today.getFullYear() ? undefined : "numeric" });
}

function requestSummary(metadata: Record<string, unknown>): string | null {
    const method = typeof metadata.method === "string" ? metadata.method : null;
    const route = typeof metadata.route === "string" ? metadata.route : null;
    const status = typeof metadata.status === "number" ? metadata.status : null;
    if (!route) return null;
    return [method, route, status ? `→ ${status}` : null].filter(Boolean).join(" ");
}

export default function ServiceDeliveryAuditPage() {
    const [logs, setLogs] = useState<Activity[]>([]);
    const [titles, setTitles] = useState<Record<string, string>>({});
    const [search, setSearch] = useState("");
    const [category, setCategory] = useState<"all" | Category>("all");
    const [expanded, setExpanded] = useState<string | null>(null);

    useEffect(() => {
        listAuditActivity({ limit: 200 }).then((res) => setLogs(res.items)).catch(console.error);
        listEngagements({ limit: 100 })
            .then((res) => setTitles(Object.fromEntries(res.items.map((e) => [e.id, e.title]))))
            .catch(console.error);
    }, []);

    const counts = useMemo(() => {
        const result: Record<string, number> = { all: logs.length };
        for (const log of logs) {
            const c = categoryOf(log);
            result[c] = (result[c] ?? 0) + 1;
        }
        return result;
    }, [logs]);

    const filtered = useMemo(() => {
        const query = search.trim().toLowerCase();
        return logs.filter((log) => {
            if (category !== "all" && categoryOf(log) !== category) return false;
            if (!query) return true;
            const title = log.entity_id ? titles[log.entity_id] ?? "" : "";
            return [displayName(log.actor, ""), log.action, activityPhrase(log.action), log.entity_type, title].join(" ").toLowerCase().includes(query);
        });
    }, [logs, search, category, titles]);

    const days = useMemo(() => {
        const groups: { day: string; items: Activity[] }[] = [];
        for (const log of filtered) {
            const day = dayLabel(log.created_at);
            const last = groups[groups.length - 1];
            if (last && last.day === day) last.items.push(log);
            else groups.push({ day, items: [log] });
        }
        return groups;
    }, [filtered]);

    return (
        <>
            <ServiceDeliveryPageTitle title="Audit logs" />
            <p className="mt-2 text-sm text-brand-text/80">Read-only operational history for engagements managed through Service Delivery.</p>

            <section className="mt-6 rounded-[10px] border border-brand-panel-border bg-brand-panel p-5">
                <div className="flex flex-wrap items-center gap-2">
                    {FILTERS.map((key) => {
                        const active = category === key;
                        const meta = key === "all" ? null : CATEGORY[key];
                        return (
                            <button
                                key={key}
                                type="button"
                                aria-pressed={active}
                                onClick={() => setCategory(key)}
                                className={cn(
                                    "inline-flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                                    active ? "border-brand-cyan/60 bg-brand-cyan/10 text-brand-cyan" : "border-brand-panel-border text-[#cbd5e1] hover:border-brand-cyan/40"
                                )}
                            >
                                {meta && <meta.icon aria-hidden="true" className="size-4" style={{ color: active ? undefined : meta.color }} />}
                                {meta ? meta.label : "All"}
                                <span className="text-brand-text/50">{counts[key] ?? 0}</span>
                            </button>
                        );
                    })}
                    <label className="ml-auto flex h-9 min-w-[240px] items-center gap-2 rounded-lg border border-brand-panel-border bg-brand-panel-deep px-3 text-brand-text/60 max-md:ml-0 max-md:w-full">
                        <Search className="size-4 shrink-0" />
                        <input
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder="Search people, actions, engagements..."
                            aria-label="Search audit logs"
                            className="w-full border-0 bg-transparent text-sm text-brand-text outline-none placeholder:text-brand-text/50"
                        />
                    </label>
                </div>

                <div className="mt-5">
                    {days.length === 0 ? (
                        <p className="m-0 rounded-lg border border-dashed border-brand-panel-border py-6 text-center text-sm text-brand-text/70">No activity matches these filters.</p>
                    ) : (
                        days.map(({ day, items }) => (
                            <Fragment key={day}>
                                <h2 className="m-0 mt-5 mb-2 text-xs font-semibold tracking-wide text-brand-text/60 uppercase first:mt-0 [font-family:inherit]!">
                                    {day} <span className="font-normal">· {items.length}</span>
                                </h2>
                                <ul className="m-0 grid list-none gap-1.5 p-0">
                                    {items.map((log) => (
                                        <AuditRow
                                            key={log.id}
                                            log={log}
                                            title={log.entity_id ? titles[log.entity_id] : undefined}
                                            open={expanded === log.id}
                                            onToggle={() => setExpanded((current) => (current === log.id ? null : log.id))}
                                        />
                                    ))}
                                </ul>
                            </Fragment>
                        ))
                    )}
                </div>
            </section>
        </>
    );
}


function AuditRow({ log, title, open, onToggle }: { log: Activity; title?: string; open: boolean; onToggle: () => void }) {
    const category = CATEGORY[categoryOf(log)];
    const isEngagement = log.entity_type === "engagement" && log.entity_id;
    const request = log.entity_type === "http_request" ? requestSummary(log.metadata ?? {}) : null;
    const hasDetails = Object.keys(log.metadata ?? {}).length > 0 || Boolean(log.entity_id);

    return (
        <li className="overflow-hidden rounded-lg border border-l-[3px] border-brand-panel-border bg-brand-panel-deep/40" style={{ borderLeftColor: category.color }}>
            <button
                type="button"
                onClick={onToggle}
                aria-expanded={open}
                className="flex w-full cursor-pointer items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[0.03]"
            >
                <span
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase"
                    style={{ color: category.color, backgroundColor: `color-mix(in srgb, ${category.color} 12%, transparent)` }}
                >
                    <category.icon aria-hidden="true" className="size-4" />
                    {category.label}
                </span>
                <span className="min-w-0 flex-1">
                    <span className="block truncate text-[15px] text-[#cbd5e1]">
                        <strong className="font-semibold text-brand-text">{displayName(log.actor, "System")}</strong>{" "}
                        {isEngagement ? activityPhrase(log.action) : activityPhrase(log.action).replace(/ (on|to)$/, "")}
                        {isEngagement && <> <strong className="font-semibold text-brand-text">{title ?? "an engagement"}</strong></>}
                    </span>
                    {request && <span className="mt-0.5 block truncate font-mono text-xs text-brand-text/50">{request}</span>}
                </span>
                <span className="shrink-0 text-sm whitespace-nowrap text-brand-text/60" title={formatDateTime(log.created_at)}>{relativeTime(log.created_at)}</span>
                {hasDetails && <ChevronDown aria-hidden="true" className={cn("size-5 shrink-0 text-brand-text/40 transition-transform", open && "rotate-180")} />}
            </button>

            {open && (
                <div className="border-t border-brand-panel-border bg-black/20 px-3.5 py-3 text-xs">
                    <dl className="m-0 grid grid-cols-[7rem_minmax(0,1fr)] gap-x-3 gap-y-1.5">
                        <dt className="text-brand-text/50">Action</dt>
                        <dd className="m-0 font-mono text-[#cbd5e1]">{log.action}</dd>
                        <dt className="text-brand-text/50">Entity</dt>
                        <dd className="m-0 font-mono break-all text-[#cbd5e1]">
                            {log.entity_type}{log.entity_id ? ` · ${log.entity_id}` : ""}
                            {isEngagement && (
                                <Link href={`/service-delivery/engagements/${log.entity_id}`} className="ml-2 font-sans text-brand-cyan hover:underline">Open engagement</Link>
                            )}
                        </dd>
                        <dt className="text-brand-text/50">When</dt>
                        <dd className="m-0 text-[#cbd5e1]">{formatDateTime(log.created_at)}</dd>
                        {Object.entries(log.metadata ?? {}).map(([key, value]) => (
                            <Fragment key={key}>
                                <dt className="text-brand-text/50">{key}</dt>
                                <dd className="m-0 font-mono break-all text-[#cbd5e1]">{typeof value === "string" ? value : JSON.stringify(value)}</dd>
                            </Fragment>
                        ))}
                    </dl>
                </div>
            )}
        </li>
    );
}