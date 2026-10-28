import { capitalize, cn } from "@/lib/utils";

export const TYPE_LABEL: Record<string, string> = { subdomain: "Subdomain", ipv4: "IPv4", ipv6: "IPv6", ip: "IP", email: "Email" };
export const TYPE_BADGE: Record<string, string> = {
    subdomain: "border-brand-blue/50 bg-brand-blue/10 text-brand-blue",
    ipv4: "border-brand-cyan/50 bg-brand-cyan/10 text-brand-cyan",
    ipv6: "border-brand-cyan/50 bg-brand-cyan/10 text-brand-cyan",
    ip: "border-brand-cyan/50 bg-brand-cyan/10 text-brand-cyan",
    email: "border-[#334155] bg-[#334155]/20 text-[#cbd5e1]",
};
export const TYPE_COLOR: Record<string, string> = { subdomain: "#60a5fa", ipv4: "#2bd8f5", ipv6: "#22d3ee", ip: "#2bd8f5", email: "#94a3b8" };
export const typeKey = (type: string) => type.toLowerCase();
export const typeLabel = (type: string) => TYPE_LABEL[typeKey(type)] ?? capitalize(type);
export const isIpType = (type: string) => ["ip", "ipv4", "ipv6"].includes(typeKey(type));

export function TypeBadge({ type }: { type: string }) {
    return (
        <span className={cn("inline-flex w-fit items-center rounded-[5px] border px-1.5 py-px text-[10px] font-semibold", TYPE_BADGE[typeKey(type)] ?? "border-[#a855f7]/50 bg-[#a855f7]/10 text-[#c084fc]")}>
            {typeLabel(type)}
        </span>
    );
}