"use client";

import type { ReactNode } from "react";

interface ServiceDeliveryModalProps {
    kicker?: string;
    title: string;
    onClose: () => void;
    children: ReactNode;
    maxWidthClassName ?:string;
}

export default function ServiceDeliveryModal ({
    kicker,
    title,
    onClose,
    children,
    maxWidthClassName = "max-w-md",
}: ServiceDeliveryModalProps) {
    return(
        <div
            role ="button"
            tabIndex={0}
            className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4"
            onClick={onClose}
            onKeyDown={(e) => e.key === "Escape" && onClose()}
        >
            <div
                role ="dialog"
                aria-modal="true"
                className={`max-h-[85vh] w-full ${maxWidthClassName} overflow-y-auto rounded-xl border border-brand-panel-border bg-brand-panel p-5`}           
                onClick={(e) => e.stopPropagation()}
                onKeyDown={(e) => e.stopPropagation()}
            >
                {kicker && <div className="text-[11px] tracking-wide text-brand-text/70 uppercase">{kicker}</div>}
                <h2 className="mt-1 text-lg font-semibold text-brand-text">{title}</h2>
                {children}
            </div>
        </div>
    );
}