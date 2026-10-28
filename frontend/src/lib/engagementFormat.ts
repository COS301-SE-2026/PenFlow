import { capitalize } from "@/lib/utils";

const DOMAIN_PREFIX = /^([a-z0-9-]+(?:\.[a-z0-9-]+)+)\s+-\s+(.+)$/i;

export function splitEngagementTitle(title: string): { domain: string | null; name: string } {
    const match = DOMAIN_PREFIX.exec(title.trim());
    return match ? { domain: match[1], name: match[2] } : { domain: null, name: title };
}

const ACRONYMS: Record<string, string> = { api: "API", ip: "IP", dns: "DNS", ssl: "SSL", tls: "TLS", iot: "IoT" };

export function formatEnumLabel(value: string): string {
    return value
        .split("_")
        .map((word) => ACRONYMS[word.toLowerCase()] ?? capitalize(word))
        .join(" ");
}

export function formatQuote(value: number | string | null | undefined): string {
    if (value === null || value === undefined || value === "") return "-";
    const amount = Number(value);
    if (Number.isNaN(amount)) return `R${value}`;
    return `R${amount.toLocaleString("en-ZA", { maximumFractionDigits: 2 })}`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function dayMonth(date: Date, withYear: boolean): string {
    const label = `${date.getDate()} ${MONTHS[date.getMonth()]}`;
    return withYear ? `${label} ${date.getFullYear()}` : label;
}

function isCurrentYear(date: Date): boolean {
    return date.getFullYear() === new Date().getFullYear();
}

export function formatShortDate(value: string): string {
    const date = new Date(value);
    return dayMonth(date, !isCurrentYear(date));
}

export function formatDateWithYear(value: string): string {
    return dayMonth(new Date(value), true);
}

export function formatDateRange(start: string | null, end: string | null): string {
    if (!start && !end) return "TBD";
    if (!start || !end) {
        const label = (value: string | null) => (value ? dayMonth(new Date(value), true) : "TBD");
        return `${label(start)} – ${label(end)}`;
    }
    const startDate = new Date(start);
    const endDate = new Date(end);
    return `${dayMonth(startDate, startDate.getFullYear() !== endDate.getFullYear())} – ${dayMonth(endDate, true)}`;
}

export function formatDateTime(value: string): string {
    const date = new Date(value);
    const time = `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
    return `${dayMonth(date, !isCurrentYear(date))}, ${time}`;
}