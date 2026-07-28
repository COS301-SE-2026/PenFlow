"use client";
import {useEffect, useState} from "react";
import Link from "next/link";
import { capitalize, cn } from "@/lib/utils";
import{fetchScanMetrics, fetchScanFindings, fetchScanAssets,fetchScanRiskHistory,
    type ScanMetrics,
    type DashboardFindingItem,
    type DashboardAssetItem,
    type RiskHistoryItem,
} from "@/lib/scanService";

interface BreakdownItem {
    label: string;
    value: number;
}

interface SummaryCardProps {
    title: string;
    value: number;
    items: BreakdownItem[];
    donutGradient: string;
}

const severityClassName: record<string, string> = {
    critical: "border-[#991b1b] text-brand-alert bg-brand-alert/10",
    high: "border-brand-orange/70 text-brand-orange bg-brand-orange/10",
    medium: "border-brand-yellow/70 text-brand-yellow bg-brand-yellow/10",
    low: "border-[#1e40af] text-[#60a5fa] bg-[#1e40af]/10",
};

const DONUT_GRADIENTS = {
    findings: "conic-gradient(#ef4444 0 35%, #f97316 35% 64%, #facc15 64% 90%, #3b82f6 90% 97%, #64748b 97% 100%)",
    assets: "conic-gradient(#3b82f6 0 15%, #14b8a6 15% 45%, #22c55e 45% 78%, #64748b 78% 100%)",
    services: "conic-gradient(#3b82f6 0 30%, #06b6d4 30% 64%, #14b8a6 64% 78%, #64748b 78% 100%)",
    technologies: "conic-gradient(#3b82f6 0 33%, #0ea5e9 33% 55%, #38bdf8 55% 77%, #64748b 77% 100%)",
};

const PANEL_CLASS_NAME = "min-w-0 rounded-[10px] border-brand-panel-border bg-[#0b1625] p-[18px]";
function SummaryCard({title, value, items, donutGradient}: SummaryCardProps) {
    return (
        <article className={cn(PANEL_CLASS_NAME, "min-h-[210px")}>
            <div className="flex items-center justify-between gap-4">
                <div>
                    <span className="mb-2 block text-[11px] font-semibold text-[#cbd5e1] uppercase">{title}</span>
                    <strong className="block text-[30px] leading-none text-foreground"> {value} </strong>
                </div>
                {items.length > 0 && (
                    <div
                        aria-hidden="true"
                        className="size-[74px] shrink-0 rounded-full"
                        style = {{
                            background: donutGradient,
                            mask: "radial-gradient(circle at center, trasparent 48%, #000 50%",
                        }}
                    />
                )}
            </div>

            {items.length > 0 ? (
                <ul className="mt-[15px] grid list-none gap-1.5 p-0">
                    {items.map((item) => (
                        <li key = {item.label} className="flex justify-between gap-3 text-[11px] text-muted-foreground">
                            <span> {item.label} </span>
                            <strong className="text-foreground"> {item.value} </strong>
                        </li>
                    ))}
                </ul>
            ): (
                <p className="mt-[15px] text-xs text-muted-foreground">No breakdown available yet.</p>
            )}
        </article>
    );
}

function riskLevelLabel(level: string): string {
    return level.split("_").map((word) => capitalize(word.toLowerCase())).join("");
}

function BreakdownItems(breakdown: Record<string, number>) : BreakdownItem[] {
    return Object.entries(breakdown).filter(([key]) => key !== "total").map(([Key, value]) => ({label:capitalize(key), value}));
}

function RiskHistoryChart({history}: {history: RiskHistoryItem[]}) {
    if (history.length < 2) {
        return <p className="mt-[15px] text-xs text-muted-foreground"> Not enough historical scans yet to chart a trend. </p>;
    }

    const width = 600;
    const height = 220;
    const step = width / (history.length -1);
    const points = history.map((item, index) => {
        const x = index * step;
        const y = height - (item.risk_score / 100) * height;
        return {x,y};
    });

    const linePoints = points.map((p) => `${p.x},${p.y}`).join(" ");
    const fillPoints = `${linePoints} ${width}, ${height} 0,${height}`;

    
}