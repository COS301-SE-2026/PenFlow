"use client";
import { useEffect } from "react";

import { cn } from "@/lib/utils";

export default function SidePanelShell({ labelledBy, onClose, children }: { labelledBy: string; onClose: () => void; children: React.ReactNode }) {
    useEffect(() => {
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        const handleKeyDown = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
        window.addEventListener("keydown", handleKeyDown);
        return () => {
            document.body.style.overflow = previousOverflow;
            window.removeEventListener("keydown", handleKeyDown);
        };
    }, [onClose]);

    return (
        <>
            <button type="button" aria-label="Close panel" onClick={onClose}
                className="fixed inset-0 z-[84] border-0 bg-black/55 animate-in fade-in duration-200 motion-reduce:animate-none" />
            <aside
                role="dialog"
                aria-modal="true"
                aria-labelledby={labelledBy}
                className={cn(
                    "fixed z-[85] flex flex-col border-brand-panel-border bg-[#0b1625] shadow-[-18px_0_50px_rgba(0,0,0,0.45)]",
                    "animate-in duration-200 motion-reduce:animate-none",
                    "sm:top-4 sm:right-4 sm:max-h-[calc(100dvh-2rem)] sm:w-[440px] sm:overflow-hidden sm:rounded-xl sm:border sm:slide-in-from-right",
                    "max-sm:inset-x-0 max-sm:bottom-0 max-sm:max-h-[85dvh] max-sm:rounded-t-xl max-sm:border-t max-sm:slide-in-from-bottom",
                )}
            >
                {children}
            </aside>
        </>
    );
}