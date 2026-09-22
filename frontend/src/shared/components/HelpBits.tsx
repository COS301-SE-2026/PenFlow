
"use client";
import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, CheckCircle2, ChevronRight } from "lucide-react"; 
import styles from "./HelpTopicModal.module.css";

export type HelpListTone = "default" | "success" | "warning";

const TONE_ICON: Record<HelpListTone, LucideIcon> = {
    default: ChevronRight,
    success: CheckCircle2,
    warning: AlertTriangle,
};

const TONE_COLOR: Record<HelpListTone, string> = {
    default: "var(--col-cyan)",
    success: "var(--col-success)",
    warning: "var(--col-alert)",
};

interface HelpListProps {
    items: ReactNode[];
    tone?: HelpListTone;
}

export function HelpList({ items, tone = "default" }: HelpListProps) {
    const Icon= TONE_ICON[tone];

    return (
        <ul className={styles.iconList}>
            {items.map((item, index) => ( <li key={index}>
                <Icon size={14} className={styles.iconListIcon} style={{ color: TONE_COLOR[tone] }} aria-hidden="true" /> 
                <span>{item}</span>
            </li>
        ))}
    </ul>
);}

interface HelpStepsProps {
    items: ReactNode[];
}

export function HelpSteps({ items }: HelpStepsProps) {
    return (
            <ol className={styles.stepList}>
                {items.map((item, index) => (
            <li key={index}>
                <span className={styles.stepNumber}>{index + 1}</span>
                <span>{item}</span>
            </li>
        ))}
    </ol>
    );
}