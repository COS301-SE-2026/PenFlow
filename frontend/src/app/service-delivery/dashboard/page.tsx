"use client";

import { useEffect, useState } from "react";
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

