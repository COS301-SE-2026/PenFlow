"use client";
import { Chart as ChartJS, ArcElement, Tooltip, Legend, type ChartOptions } from "chart.js";
import { Doughnut } from "react-chartjs-2";
import Link from "next/link";
import { ChevronRight, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

ChartJS.register(ArcElement, Tooltip, Legend);

export interface BreakdownItem {
    label: string;
    value: number;
}

interface SummaryCardProps {
    title: string;
    value: number;
    items: BreakdownItem[];
    colors: string[];
    icon: LucideIcon;
    accentClassName: string;
    keepBreakdownOnPhones?: boolean;
    layout?: "stacked" | "side" | "compact";
    className?: string;
    subtitle?: React.ReactNode;
    href?: string;
    delta?: { value: number; upIsBad?: boolean } | null;
}

export const FINDINGS_COLORS: Record<string, string> = {
    critical: "#ef4444",
    high: "#f97316",
    medium: "#facc15",
    low: "#3b82f6",
    info: "#64748b",
};

export const donutTooltipOptions: ChartOptions<"doughnut">["plugins"] = {
    legend: {display: false},
    tooltip: {
        backgroundColor: "#091628",
        borderColor: "rgba(43,180,220,0.3)",
        borderWidth: 1,
        titleColor: "#e5f3ff",
        bodyColor: "#e5f3ff",
        padding: 8,
    },
};

const donutOptions: ChartOptions<"doughnut"> = {
    cutout: "62%",
    plugins: donutTooltipOptions,
    maintainAspectRatio: false,
};

const flatDonutOptions: ChartOptions<"doughnut"> = {
    ...donutOptions,
    plugins: { ...donutOptions.plugins, tooltip: { enabled: false } },
};

export const PANEL_CLASS_NAME = "min-w-0 rounded-[10px] border-brand-panel-border bg-[#0b1625] p-[18px]";
export function SummaryCard({title, value, items, colors, icon: Icon, accentClassName, keepBreakdownOnPhones = false, layout = "stacked", className, subtitle, href, delta}: SummaryCardProps) {
    const total = items.reduce((sum, item) => sum + item.value, 0);
    const phoneHidden = keepBreakdownOnPhones ? "" : "max-[650px]:hidden";

    if (layout === "compact") {
        const shown = items.filter((item) => item.value > 0);
        const showChart = shown.length > 1;
        const visibleLegend = shown.slice(0, 4);
        const hiddenCount = shown.length - visibleLegend.length;
        const deltaTone = !delta || delta.value === 0 ? "text-[#94a3b8]"
            : (delta.value > 0) === Boolean(delta.upIsBad) ? "text-brand-alert" : "text-brand-success";
        const body = (
            <>
                <div className="flex items-center justify-between gap-2">
                    <span className="flex min-w-0 items-center gap-2 text-[11px] font-semibold text-[#cbd5e1] uppercase">
                        <span className={cn("grid size-7 shrink-0 place-items-center rounded-lg", accentClassName)}>
                            <Icon aria-hidden="true" className="size-4" />
                        </span>
                        <span className="truncate">{title}</span>
                    </span>
                    {href && (
                        <span className="inline-flex shrink-0 items-center gap-0.5 text-[11px] text-brand-cyan opacity-70 transition-opacity group-hover:opacity-100">
                            View <ChevronRight className="size-3.5" />
                        </span>
                    )}
                </div>

                <div className="flex items-center gap-4">
                    {showChart ? (
                        <div className={cn("relative size-16 shrink-0", phoneHidden)}>
                            <span className="pointer-events-none absolute inset-0 grid place-items-center text-[15px] font-bold text-foreground">{value}</span>
                            <Doughnut
                                data={{ labels: shown.map((i) => i.label), datasets: [{ data: shown.map((i) => i.value), backgroundColor: shown.map((i) => colors[items.indexOf(i)]), borderWidth: 0 }] }}
                                options={flatDonutOptions}
                            />
                        </div>
                    ) : (
                        <strong className={cn("block shrink-0 text-[30px] leading-none text-foreground", showChart && "hidden")}>{value}</strong>
                    )}
                    {showChart && <strong className="hidden text-2xl leading-none text-foreground max-[650px]:block">{value}</strong>}
                    {shown.length > 0 ? (
                        <ul className={cn("m-0 grid min-w-0 flex-1 list-none gap-1 p-0", phoneHidden)}>
                            {visibleLegend.map((item) => (
                                <li key={item.label} className="flex min-w-0 items-center justify-between gap-2 text-[11px]">
                                    <span className="flex min-w-0 items-center gap-1.5 text-[#cbd5e1]">
                                        <span className="size-2 shrink-0 rounded-full" style={{ backgroundColor: colors[items.indexOf(item)] }} />
                                        <span className="truncate" title={item.label}>{item.label}</span>
                                    </span>
                                    <strong className="shrink-0 text-foreground">{item.value}</strong>
                                </li>
                            ))}
                            {hiddenCount > 0 && <li className="text-[10px] text-[#94a3b8]">+{hiddenCount} more</li>}
                        </ul>
                    ) : (
                        <p className={cn("m-0 text-[11px] text-[#64748b]", phoneHidden)}>Nothing yet</p>
                    )}
                </div>

                {(subtitle || delta) && (
                    <div className="mt-auto flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-[11px]">
                        {subtitle && <span className="min-w-0 text-[#94a3b8]">{subtitle}</span>}
                        {delta && (
                            <span className={cn("shrink-0 font-semibold", deltaTone)} title="Change since the previous scan of this domain">
                                {delta.value === 0 ? "No change" : `${delta.value > 0 ? "▲" : "▼"} ${Math.abs(delta.value)}`} <span className="font-normal text-[#64748b]">vs last scan</span>
                            </span>
                        )}
                    </div>
                )}
            </>
        );
        const cardClass = cn(PANEL_CLASS_NAME, "group flex flex-col gap-3 border border-transparent max-[650px]:p-3", href && "no-underline transition-colors hover:border-brand-cyan/40", className);
        return href
            ? <Link href={href} aria-label={`${title}: ${value}. View ${title.toLowerCase()}`} className={cardClass}>{body}</Link>
            : <article className={cardClass}>{body}</article>;
    }

    if (layout === "side") {
        return (
            <article
                aria-label={`${title}: ${value}`}
                className={cn(PANEL_CLASS_NAME, "grid grid-cols-[72px_minmax(0,1fr)] items-center gap-x-5 py-3.5 max-[650px]:p-3", className)}
            >
                {total > 0 ? (
                    <>
                        <div className={cn("relative size-[72px]", phoneHidden)}>
                            <span className="pointer-events-none absolute inset-0 grid place-items-center text-[15px] font-bold text-foreground">{value}</span>
                            <Doughnut
                                data={{
                                    labels: items.map((item) => item.label),
                                    datasets: [{ data: items.map((item) => item.value), backgroundColor: colors, borderWidth: 0 }],
                                }}
                                options={flatDonutOptions}
                            />
                        </div>
                        <ul className={cn("m-0 grid list-none grid-flow-col grid-cols-[repeat(2,max-content)] grid-rows-3 gap-x-8 gap-y-1 p-0", phoneHidden)}>
                            {items.map((item, index) => (
                                <li key={item.label} className="grid min-w-0 grid-cols-[4.75rem_auto] items-center gap-1.5 text-[11px]">
                                    <span className="flex min-w-0 items-center gap-1.5 truncate" style={{ color: colors[index] }}>
                                        <span className="size-2 shrink-0 rounded-full" style={{ backgroundColor: colors[index] }} />
                                        {item.label}
                                    </span>
                                    <strong className="text-foreground">{item.value}</strong>
                                </li>
                            ))}
                        </ul>
                    </>
                ) : (
                    <p className="col-span-2 m-0 flex items-center gap-2 text-xs text-muted-foreground">
                        <Icon aria-hidden="true" className="size-4" /> No {title.toLowerCase()} yet.
                    </p>
                )}
            </article>
        );
    }

    return (
        <article className={cn(PANEL_CLASS_NAME, "min-h-[210px] max-[650px]:min-h-0 max-[650px]:p-3", className)}>
            <div className="flex items-center justify-between gap-4">
                <div>
                    <span className="mb-2 flex items-center gap-2 text-[11px] font-semibold text-[#cbd5e1] uppercase">
                        <span className={cn("grid size-7 shrink-0 place-items-center rounded-lg", accentClassName)}>
                            <Icon aria-hidden="true" className="size-4" />
                        </span>
                        {title}
                    </span>
                    <strong className="block text-[30px] leading-none text-foreground max-[650px]:text-2xl"> {value} </strong>
                </div>
                {total > 0 && (
                    <div className={cn("size-[74px] shrink-0", phoneHidden)}>
                        <Doughnut data = {{
                            labels: items.map((item) => item.label),
                            datasets: [{
                                data: items.map((item) => item.value),
                                backgroundColor: colors,
                                borderWidth: 0,
                            }],
                        }}
                        options = {donutOptions}
                    />
                    </div>
                )}
            </div>

            {total > 0 ? (
                <ul className={cn("mt-[15px] grid list-none gap-1.5 p-0", phoneHidden)}>
                    {items.map((item, index) => (
                        <li key = {item.label} className="flex justify-between gap-3 text-[11px]">
                            <span style={{color: colors[index]}}> {item.label} </span>
                            <strong className="text-foreground"> {item.value} </strong>
                        </li>
                    ))}
                </ul>
            ): (
                <p className={cn("mt-[15px] text-xs text-muted-foreground", phoneHidden)}>No breakdown available yet.</p>
            )}
        </article>
    );
}