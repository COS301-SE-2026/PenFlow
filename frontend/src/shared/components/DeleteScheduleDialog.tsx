"use client";

import { useEffect, useId, useRef } from "react";
import { LoaderCircle, Trash2 } from "lucide-react";

export default function DeleteScheduleDialog({
    domain,
    busy,
    error,
    onClose,
    onConfirm,
}: {
    domain: string;
    busy: boolean;
    error: string | null;
    onClose: () => void;
    onConfirm: () => void;
}) {
    const dialogRef = useRef<HTMLDialogElement>(null);
    const cancelRef = useRef<HTMLButtonElement>(null);
    const titleId = useId();
    const descriptionId = useId();

    useEffect(() => {
        const dialog = dialogRef.current;
        if (!dialog) return;

        dialog.showModal();
        cancelRef.current?.focus();

        return () => dialog.close();
    }, []);

    return (
        <dialog
            ref={dialogRef}
            role="alertdialog"
            aria-labelledby={titleId}
            aria-describedby={descriptionId}
            onCancel={(event) => {
                event.preventDefault();
                if (!busy) onClose();
            }}
            onClick={(event) => {
                if (event.target !== event.currentTarget || busy) return;

                const bounds = event.currentTarget.getBoundingClientRect();
                const outside =
                    event.clientX < bounds.left ||
                    event.clientX > bounds.right ||
                    event.clientY < bounds.top ||
                    event.clientY > bounds.bottom;

                if (outside) onClose();
            }}
            className="m-auto w-[calc(100%_-_2rem)] max-w-md overflow-hidden rounded-2xl border border-brand-panel-border bg-brand-panel p-0 text-slate-100 shadow-2xl backdrop:bg-black/70 backdrop:backdrop-blur-sm"
        >
            <div className="p-6">
                <div className="mb-4 grid size-11 place-items-center rounded-xl border border-red-400/25 bg-red-400/10 text-red-300">
                    <Trash2 aria-hidden="true" className="size-5" />
                </div>

                <h2
                    id={titleId}
                    className="m-0 text-xl font-semibold"
                >
                    Delete recurring scan?
                </h2>

                <p
                    id={descriptionId}
                    className="mt-3 text-sm leading-6 text-slate-300"
                >
                    Remove the schedule for{" "}
                    <strong className="break-all text-slate-100">
                        {domain}
                    </strong>
                    ? Existing scans and reports will remain available.
                </p>

                {error && (
                    <p role="alert" className="mt-4 text-sm text-red-300">
                        {error}
                    </p>
                )}

                <div className="mt-6 flex flex-wrap justify-end gap-3">
                    <button
                        ref={cancelRef}
                        type="button"
                        disabled={busy}
                        onClick={onClose}
                        className="min-h-11 rounded-lg border border-brand-panel-border bg-brand-panel-deep px-4 text-sm font-semibold text-slate-100 hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-300 disabled:opacity-50"
                    >
                        Keep schedule
                    </button>

                    <button
                        type="button"
                        disabled={busy}
                        onClick={onConfirm}
                        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-red-400/40 bg-red-400/10 px-4 text-sm font-semibold text-red-200 hover:bg-red-400/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-300 disabled:opacity-50"
                    >
                        {busy && (
                            <LoaderCircle
                                aria-hidden="true"
                                className="size-4 animate-spin motion-reduce:animate-none"
                            />
                        )}

                        {busy ? "Deleting…" : "Delete schedule"}
                    </button>
                </div>
            </div>
        </dialog>
    );
}