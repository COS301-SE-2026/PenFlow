"use client";

import { useEffect, useState } from "react";

export function useRetestWindow(
    scheduledEndDate: string | null | undefined,
) {
    const [now, setNow] = useState<number | null>(null);

    useEffect(() => {
        const update = () => setNow(Date.now());
        update();

        const timer = window.setInterval(update, 30_000);
        window.addEventListener("focus", update);

        return () => {
            window.clearInterval(timer);
            window.removeEventListener("focus", update);
        };
    }, []);

    const end = scheduledEndDate
        ? Date.parse(`${scheduledEndDate}T00:00:00Z`)
        : NaN;

    const expiresAt = end + 8 * 86_400_000;
    const valid = Number.isFinite(expiresAt);
    const allowed = now !== null && valid && now < expiresAt;

    const deadline = valid
        ? new Date(end + 7 * 86_400_000).toISOString().slice(0, 10)
        : null;

    const message = !valid
        ? "Retesting requires a scheduled end date."
        : now === null
            ? "Checking retesting availability…"
            : allowed
                ? `Retesting is available through ${deadline} (UTC).`
                : `The retesting window expired after ${deadline} (UTC).`;

    return { allowed, message };
}