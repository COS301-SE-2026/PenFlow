"use client";

import {
    AlertCircle,
    CheckCircle2,
    LoaderCircle,
    Mail,
    Send,
    X,
} from "lucide-react";
import {
    type FormEvent,
    useState,
} from "react";

import { sendReportEmail } from "@/lib/scanService";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

interface EmailReportDialogProps {
    scanId: string;
    domain: string;
    onClose: () => void;
}

export default function EmailReportDialog({
    scanId,
    domain,
    onClose,
}: EmailReportDialogProps) {
    const [email, setEmail] = useState("");
    const [sending, setSending] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function handleSubmit(
        event: FormEvent<HTMLFormElement>
    ) {
        event.preventDefault();
        const recipient = email.trim();

        if(!recipient || sending) return;

        setSending(true);
        setError(null);

        try {
            await sendReportEmail(
                scanId,
                recipient,
            );
            setSent(true);
        } catch (caughtError) {
            setError(
                caughtError instanceof Error ? caughtError.message : "Unable to send the report."
            );
        } finally {
            setSending(false);
        }
    }

    return (
        <div className="fixed inset-0 z-[60] grid place-items-center bg-black/75 p-4 backdrop-blur-sm"
        role="presentation" onMouseDown={(event) => {
            if(event.target === event.currentTarget && !sending) {
                onClose();
            }
        }}>
            <div role="dialog" aria-modal="true" aria-labelledby="email-report-title" aria-describedby="email-report-description"
            className="w-full max-w-md overflow-hidden rounded-2xl border border-brand-panel-border bg-brand-panel shadow-[0_24px_80px_rgba(0,0,0,0.65)]"
            onKeyDown={(event) => {
                if(event.key === "Escape" && !sending) {
                    onClose();
                }
            }}>
                <div className="flex items-start justify-between gap-4 border-b border-brand-panel-border px-5 py-4">
                    <div className="flex min-w-0 items-center gap-3">
                        <div className="grid size-10 shrink-0 place-items-center rounded-xl border border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan">
                            <Mail className="size-5" />
                        </div>
                        <div className="min-w-0">
                            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-cyan">
                                Scan report
                            </p>
                            <h2 id="email-report-title" className="truncate text-lg font-semibold text-foreground">
                                Email report
                            </h2>
                        </div>
                    </div>
                    <Button type="button" variant="ghost" size="icon" aria-label="Close email report dialog" disabled={sending} onClick={onClose}
                    className="text-muted-foreground hover:text-foreground">
                        <X className="size-4" />
                    </Button>
                </div>

                {sent ? (
                    <div className="flex flex-col items-center gap-4 px-6 py-8 text-center">
                        <div className="grid size-14 place-items-center rounded-full border border-brand-success/40 bg-brand-success/10 text-brand-success">
                            <CheckCircle2 className="size-7" />
                        </div>
                        <div>
                            <p className="font-semibold text-foreground">
                                Report queued for delivery
                            </p>
                            <p className="mt-1 break-all text-sm text-muted-foreground">
                                PenFlow will send the {domain} report to {" "}
                                <span className="text-foreground">
                                    {email.trim()}
                                </span>
                                .
                            </p>
                        </div>
                        <Button type="button" onClick={onClose} className="bg-brand-cyan px-5 text-[#06111d] hover:bg-brand-cyan/85">
                            Done
                        </Button>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-5 px-6 py-5">
                        <p id="email-report-description" className="text-sm leading-6 text-muted-foreground">
                            Send the completed report for {" "}
                            <span className="font-medium text-foreground">
                                {domain}
                            </span>{" "}
                            as a PDF attachment.
                        </p>
                        <div className="space-y-2">
                            <Label htmlFor="report-recipient" className="text-foreground">
                                Recipient email
                            </Label>
                            <Input id="report-recipient" type="email" autoComplete="email" autoFocus required value={email} disabled={sending}
                            placeholder="name@company.com" onChange={(event) => {
                                setEmail(event.target.value);
                                setError(null);
                            }}
                            aria-invalid={Boolean(error)} aria-describedby={
                                error ? "email-report-error" : undefined
                            }
                            className="h-11 border-brand-panel-border bg-[#07111f] px-3 text-foreground focus-visible:border-brand-cyan/60 focus-visible:ring-brand-cyan/15" />
                            {error && (
                                <p id="email-report-error" className="flex items-start gap-2 text-sm text-brand-alert" role="alert">
                                    <AlertCircle className="mt-0.5 size-4 shrink-0" />
                                    {error}
                                </p>
                            )}
                        </div>

                        <div className="flex flex-wrap justify-end gap-2 border-t border-brand-panel-border pt-4">
                            <Button type="button" variant="outline" disabled={sending} onClick={onClose} className="border-brand-panel-border">
                                Cancel
                            </Button>

                            <Button type="submit" disabled={!email.trim() || sending} className="min-w-32 bg-brand-cyan text-[#06111d] hover:bg-brand-cyan/85">
                                {sending ? (
                                    <>
                                        <LoaderCircle className="size-4 animate-spin" />
                                        Sending
                                    </>
                                ) : (
                                    <>
                                        <Send className="size-4" />
                                        Send report
                                    </>
                                )}
                            </Button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}