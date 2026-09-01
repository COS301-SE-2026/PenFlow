//styling for service delivery 

import type { AssessmentType, EngagementStatus, FindingStatus, RetestStatus, Severity, UserSummary } from "@/lib/serviceDeliveryTypes";

export const assessmentTypeLabels: Record<AssessmentType, string> = {
     web_application: "Web Application",
    mobile_application: "Mobile Application",
    api: "API",
    network: "Network",
    cloud: "Cloud",
    other: "Other",
};

export const statusLabels: Record<EngagementStatus, string> = {
    requested: "Requested",
    scoping: "Scoping",
    scheduled: "Scheduled",
    in_progress: "In Progress",
    review: "Review",
    completed: "Completed",
    cancelled: "Cancelled",
};

export const statusPillClass: Record<EngagementStatus, string> = {
    requested: "border-brand-alert/40 bg-brand-alert/10 text-brand-alert",
    scoping: "border-brand-orange/40 bg-brand-orange/10 text-brand-orange",
    scheduled: "border-brand-cyan/40 bg-brand-cyan/10 text-brand-cyan",
    in_progress: "border-brand-blue/40 bg-brand-blue/10 text-brand-blue",
    review: "border-purple-400/40 bg-purple-400/10 text-purple-300",
    completed: "border-brand-success/40 bg-brand-success/10 text-brand-success",
    cancelled: "border-brand-alert/40 bg-brand-alert/10 text-brand-alert",
};

export const statusDotClass: Record<EngagementStatus, string> = {
    requested: "bg-brand-alert",
    scoping: "bg-brand-orange",
    scheduled: "bg-brand-cyan",
    in_progress: "bg-brand-blue",
    review: "bg-purple-400",
    completed: "bg-brand-success",
    cancelled: "bg-brand-alert",
};

export const severityClass: Record<Severity, string> = {
    info: "text-muted-foreground font-semibold",
    low: "text-brand-blue font-semibold",
    medium: "text-brand-yellow font-semibold",
    high: "text-brand-orange font-semibold",
    critical: "text-brand-alert font-semibold",
};

export const findingStatusClass: Record<FindingStatus, string> = {
    open:"text-brand-alert",
    in_progress:"text-brand-blue",
    resolved:"text-brand-success",
    accepted_risk:"text-brand-orange",
    false_positive:"text-muted-foreground",
};

export const retestStatusPillClass: Record<RetestStatus, string> = {
    requested:"border-brand-panel-border bg-brand-panel-deep text-muted-foreground",
    in_progress:"border-purple-400/40 bg-purple-400/10 text-purple-300",
    still_vulnerable:"border-brand-alert/40 bg-brand-alert/10 text-brand-alert",
    resolved:"border-brand-success/40 bg-brand-success/10 text-brand-success",
};


const KNOWN_AVAILABILITY_DOT: Record<string, string> = {
    available:"bg-brand-success",
    engaged:"bg-brand-orange",
    unavailable:"bg-brand-alert",
};

export function availabilityDotClass(status: string): string {
    return KNOWN_AVAILABILITY_DOT[status] ?? "bg-muted-foreground";
}

export const controlFieldClass =
    "border-brand-panel-border bg-brand-panel-deep text-brand-text placeholder:text-brand-text/50 focus-visible:border-brand-cyan focus-visible:ring-brand-cyan/30";

export const whiteOutlineButtonClass =
    "border-white/70 bg-transparent text-white hover:border-white hover:bg-white/10 hover:text-white " +
    "dark:border-white/70 dark:bg-transparent dark:text-white dark:hover:border-white dark:hover:bg-white/10 dark:hover:text-white";

export function formatLabel(value: string): string {
    return value
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

export function displayName(user: UserSummary | null | undefined, fallback = "Unassigned"): string {
    if (!user) return fallback;
    return user.full_name ?? user.email ?? fallback;
}

export function formatDate(value: string | null | undefined): string {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString("en-ZA", { month: "short", day: "numeric", year: "numeric" });
}

export function formatDateTime(value: string | null | undefined): string {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("en-ZA", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function formatDateRange(start: string | null | undefined, end: string | null | undefined): string {
     if(!start || !end) return "-";
     return `${formatDate(start)} - ${formatDate(end)}`;
}

export function formatCurrency(value: string | null | undefined): string {
    if (value === null || value === undefined || value === "") return "-";
    const amount = Number(value);
    if (Number.isNaN(amount)) return value;
    return `R ${amount.toLocaleString("en-ZA", { minimumFractionDigits: 2 })}`;
}

export function downloadTextFile(filename: string, content: string): void {
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function downloadBlob(filename: string, blob: Blob): void {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
}
