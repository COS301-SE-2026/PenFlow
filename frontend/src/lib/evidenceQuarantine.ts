export type EvidenceQuarantineStatus =
    | "pending"
    | "clean"
    | "rejected"
    | "failed";

export function evidenceStatusLabel(
    status: EvidenceQuarantineStatus | undefined,
): string {
    switch (status) {
        case "clean":
            return "Security check passed";
        case "rejected":
            return "Blocked by security check";
        case "failed":
            return "Security check failed";
        default:
            return "Awaiting security check";
    }
}