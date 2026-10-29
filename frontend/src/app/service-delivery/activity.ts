export const SYSTEM_ACTIVITY = /^(sensitive_request|http_request|auth\.|session\.)/;

export const ACTIVITY_PHRASE: Record<string, string> = {
    "engagement.created": "requested",
    "engagement.claimed": "claimed",
    "engagement.scheduled": "scheduled",
    "engagement.assigned": "assigned a pentester to",
    "engagement.pentester_assigned": "assigned a pentester to",
    "engagement.started": "started testing",
    "engagement.submitted_for_review": "submitted for review",
    "engagement.completed": "completed",
    "engagement.cancelled": "cancelled",
    "engagement.comment_created": "sent a message on",
    "finding.created": "logged a finding on",
    "finding.submitted_for_review": "submitted a finding on",
    "finding.returned_for_revision": "sent a finding back on",
    "retest.requested": "requested a retest on",
    "retest.resolved": "confirmed a fix on",
    "pentester.created": "added a pentester",
    "pentester.deactivated": "deactivated a pentester",
    "report.download_authorised": "downloaded a report",
    "sensitive_request.rejected": "was blocked from a protected request",
};

export function activityPhrase(action: string): string {
    return ACTIVITY_PHRASE[action] ?? action.replace(/[._]/g, " ").toLowerCase();
}

export function relativeTime(value: string): string {
    const minutes = Math.floor((Date.now() - new Date(value).getTime()) / 60_000);
    if (Number.isNaN(minutes)) return "";
    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} h ago`;
    const days = Math.floor(hours / 24);
    return days === 1 ? "Yesterday" : `${days} days ago`;
}