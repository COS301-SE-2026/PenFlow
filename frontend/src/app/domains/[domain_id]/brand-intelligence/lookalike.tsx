export const TECHNIQUE_LABEL: Record<string, string> = {
    tld_swap: "Different extension",
    homoglyph: "Look-alike letter",
    omission: "Missing letter",
    insertion: "Extra letter",
    transposition: "Swapped letters",
    hyphenation: "Added hyphen",
    addition: "Added word",
    bitsquatting: "One-bit change",
};
export function technique_label(type: string | undefined): string | null
{
    if (!type) return null;
    return TECHNIQUE_LABEL[type] ?? type.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

export function LookAlikeDomain({ candidate, original }: { candidate: string; original: string | null })
{
    if (!original || !original.includes(".") || candidate === original)
        return <>{candidate}</>;
    const a = candidate.toLowerCase();
    const b = original.toLowerCase();
    let prefix = 0;
    while (prefix < a.length && prefix < b.length && a[prefix] === b[prefix]) prefix++;
    let suffix = 0;
    while (
        suffix < a.length - prefix &&
        suffix < b.length - prefix &&
        a[a.length - 1 - suffix] === b[b.length - 1 - suffix]
    ) suffix++;
    const changed = candidate.slice(prefix, candidate.length - suffix);
    return (
        <>
            {candidate.slice(0, prefix)}
            {changed ? (
                <mark className="rounded-sm bg-brand-alert/20 px-px text-brand-alert">{changed}</mark>
            ) : (
                <span
                    aria-label="missing characters"
                    title={`Missing "${original.slice(prefix, original.length - suffix)}"`}
                    className="mx-px inline-block h-3.5 w-0.5 translate-y-0.5 rounded-full bg-brand-alert"
                />
            )}
            {candidate.slice(candidate.length - suffix)}
        </>
    );
}