import { listEngagements } from "@/lib/serviceDeliveryService";
import type { EngagementListItem } from "@/lib/serviceDeliveryTypes";

export interface Workload { testing: number; scheduled: number; review: number }

export const EMPTY_WORKLOAD: Workload = { testing: 0, scheduled: 0, review: 0 };

export const WORKLOAD_PARTS: { key: keyof Workload; label: string; status: string; color: string }[] = [
    { key: "testing", label: "testing", status: "in_progress", color: "#facc15" },
    { key: "scheduled", label: "scheduled", status: "scheduled", color: "#a855f7" },
    { key: "review", label: "in review", status: "review", color: "#f97316" },
];

export function workloadTotal(w: Workload | undefined): number {
    return w ? w.testing + w.scheduled + w.review : 0;
}

export async function loadWorkload(): Promise<{
    workload: Record<string, Workload>;
    titles: Record<string, string>;
    byPentester: Record<string, EngagementListItem[]>;
}> {
    const workload: Record<string, Workload> = {};
    const titles: Record<string, string> = {};
    const byPentester: Record<string, EngagementListItem[]> = {};
    let offset = 0;
    for (;;) {
        const page = await listEngagements({ assigned: true, limit: 100, offset });
        for (const engagement of page.items) {
            titles[engagement.id] = engagement.title;
            const id = engagement.assigned_pentester?.id;
            if (!id) continue;
            (byPentester[id] ??= []).push(engagement);
            const counts = (workload[id] ??= { ...EMPTY_WORKLOAD });
            if (engagement.status === "in_progress" || engagement.status === "retesting") counts.testing += 1;
            else if (engagement.status === "scheduled") counts.scheduled += 1;
            else if (engagement.status === "review") counts.review += 1;
        }
        if (!page.pagination.has_more || page.items.length === 0) break;
        offset += page.items.length;
    }
    return { workload, titles, byPentester };
}