"use client";
import { useEffect, useState } from "react";
import { SlidersHorizontal } from "lucide-react";

import { cn } from "@/lib/utils";

const WIDE_LAYOUT_QUERY = "(min-width: 1100px)";
const FILTERS_INLINE_QUERY = "(min-width: 720px)";
const PHONE_INLINE_QUERY = "(min-width: 640px)";

export const DETAIL_SHEET_CLASS_NAME =
    "max-[1100px]:fixed max-[1100px]:inset-x-0 max-[1100px]:bottom-0 max-[1100px]:z-50 max-[1100px]:flex max-[1100px]:max-h-[85dvh] max-[1100px]:flex-col max-[1100px]:rounded-b-none max-[1100px]:border-b-0 max-[1100px]:shadow-[0_-12px_40px_rgb(0_0_0/0.5)]";

export const DETAIL_SHEET_BODY_CLASS_NAME = "max-[1100px]:min-h-0 max-[1100px]:flex-1 max-[1100px]:overscroll-contain";

function matches(query: string): boolean {
    return typeof window !== "undefined" && window.matchMedia(query).matches;
}

export function isWideLayout(): boolean {
    return matches(WIDE_LAYOUT_QUERY);
}

function useSheetBehaviour(onClose: () => void, inlineQuery: string) {
    useEffect(() => {
        if (matches(inlineQuery)) return;

        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";

        function handleKeyDown(e: KeyboardEvent) {
            if (e.key === "Escape") onClose();
        }
        window.addEventListener("keydown", handleKeyDown);

        return () => {
            document.body.style.overflow = previousOverflow;
            window.removeEventListener("keydown", handleKeyDown);
        };
    }, [onClose, inlineQuery]);
}

export function DetailSheetBackdrop({ onClose }: { onClose: () => void }) {
    useSheetBehaviour(onClose, WIDE_LAYOUT_QUERY);

    return (
        <button
            type="button"
            aria-label="Close details"
            onClick={onClose}
            className="fixed inset-0 z-40 hidden border-0 bg-black/60 max-[1100px]:block"
        />
    );
}

export function PhoneSheetBackdrop({ onClose, label = "Close" }: { onClose: () => void; label?: string }) {
    useSheetBehaviour(onClose, PHONE_INLINE_QUERY);

    return (
        <button
            type="button"
            aria-label={label}
            onClick={onClose}
            className="fixed inset-0 z-40 hidden border-0 bg-black/60 max-sm:block"
        />
    );
}

function FilterSheetBackdrop({ onClose }: { onClose: () => void }) {
    useSheetBehaviour(onClose, FILTERS_INLINE_QUERY);

    return (
        <button
            type="button"
            aria-label="Close filters"
            onClick={onClose}
            className="fixed inset-0 z-40 hidden border-0 bg-black/60 max-[720px]:block"
        />
    );
}

export function FilterSheet({ activeCount, children }: { activeCount: number; children: React.ReactNode }) {
    const [open, setOpen] = useState(false);
    const close = () => setOpen(false);

    return (
        <>
            <button
                type="button"
                onClick={() => setOpen(true)}
                aria-label={activeCount > 0 ? `Filters, ${activeCount} active` : "Filters"}
                className="hidden min-h-10 items-center gap-2 rounded-lg border border-brand-panel-border bg-brand-panel-deep px-3 text-sm text-foreground max-[720px]:inline-flex"
            >
                <SlidersHorizontal className="size-4" />
                Filters
                {activeCount > 0 && (
                    <span className="grid size-5 place-items-center rounded-full bg-brand-cyan text-[11px] font-bold text-[#04121f]">
                        {activeCount}
                    </span>
                )}
            </button>

            {open && <FilterSheetBackdrop onClose={close} />}

            <div
                className={cn(
                    "min-[720px]:contents",
                    open
                        ? "max-[720px]:fixed max-[720px]:inset-x-0 max-[720px]:bottom-0 max-[720px]:z-50 max-[720px]:grid max-[720px]:gap-3 max-[720px]:rounded-t-xl max-[720px]:border max-[720px]:border-b-0 max-[720px]:border-brand-panel-border max-[720px]:bg-[#0b1625] max-[720px]:p-4 max-[720px]:pb-6 max-[720px]:shadow-[0_-12px_40px_rgb(0_0_0/0.5)]"
                        : "max-[720px]:hidden"
                )}
            >
                <div className="hidden items-center justify-between max-[720px]:flex">
                    <h3 className="m-0 text-sm font-semibold text-foreground uppercase">Filters</h3>
                    <button type="button" onClick={close} className="border-0 bg-transparent text-sm font-medium text-brand-cyan">
                        Done
                    </button>
                </div>
                {children}
            </div>
        </>
    );
}