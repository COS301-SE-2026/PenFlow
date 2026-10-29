export const PANEL = "min-w-0 rounded-[10px] border border-transparent bg-[#0b1625] p-[18px]";

export const SECTION_TITLE = "m-0 text-[13px] text-foreground uppercase";

export const LABEL = "m-0 text-[11px] font-semibold text-[#cbd5e1] uppercase";

export const ICON_BADGE = "grid size-7 shrink-0 place-items-center rounded-lg";

export const TAG = "inline-flex shrink-0 items-center rounded-[5px] border px-2 py-0.5 text-[9px] font-semibold uppercase";

export const RISK_TAG: Record<"critical" | "high" | "medium" | "low", string> = {
    critical: "border-[#991b1b] bg-brand-alert/10 text-brand-alert",
    high: "border-brand-orange/70 bg-brand-orange/10 text-brand-orange",
    medium: "border-brand-yellow/70 bg-brand-yellow/10 text-brand-yellow",
    low: "border-brand-success/60 bg-brand-success/10 text-brand-success",
};

export const FIELD = "h-9 rounded-md border border-brand-panel-border bg-brand-panel-deep text-[13px] text-foreground outline-none placeholder:text-muted-foreground focus:border-brand-cyan";