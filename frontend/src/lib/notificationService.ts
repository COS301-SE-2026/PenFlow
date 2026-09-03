import { authenticatedFetch } from "@/lib/authFetch";

const API_BASE = "/api/notifications";

export type NotificationType = 
    | "engagement.requested"
    | "engagement.claimed"
    | "engagement.assigned"
    | "engagement.scheduled"
    | "engagement.reassigned"
    | "engagement.rescheduled"
    | "engagement.started"
    | "engagement.review_required"
    | "engagement.review_returned"
    | "engagement.completed"
    | "engagement.cancelled"
    | "message.received"
    | "retest.requested"
    | "retest.completed"
    | "report.ready"


export interface NotificationItem {
    id: string;
    type: NotificationType;
    title: string;
    message: string;
    is_read: boolean;
    read_at: string | null;
    engagement_id: string | null;
    metadata: Record<string, unknown>;
    created_at: string;
}

export interface NotificationListResponse {
    items: NotificationItem[];
    unread_count: number;
    pagination: {
        total: number;
        limit: number;
        offset: number;
        has_more: boolean;
    };
}

export interface MarkNotificationsReadResponse {
    marked_read: number;
}

async function parseError(
    response: Response,
    fallback: string,
): Promise<Error> {
    const body = await response.json().catch(() => ({ detail: fallback }));
    return new Error(body.detail ?? fallback);
}


export async function fetchNotifications(options?: {
    unreadOnly?: boolean;
    limit?: number;
    offset?: number;
}): Promise<NotificationListResponse> {
    const query = new URLSearchParams({
        unread_only: String(options?.unreadOnly ?? false),
        limit: String(options?.limit ?? 20),
        offset: String(options?.offset ?? 0),
    });

    const response = await authenticatedFetch(
        `${API_BASE}?${query.toString()}`,
    );

    if(!response.ok) {
        throw await parseError(response, "Failed to load notifications");
    }

    return response.json()
}

export async function markNotificationRead(
    notificationId: string,
): Promise<NotificationItem> {
    const response = await authenticatedFetch(
        `${API_BASE}/${notificationId}/read`,
        { method: "PATCH" },
    );

    if(!response.ok) {
        throw await parseError(
            response,
            "Failed to mark notifications as read",
        );
    }
    return response.json()
}

export async function markAllNotificationsRead(): Promise<MarkNotificationsReadResponse> {
    const response = await authenticatedFetch(`${API_BASE}/read-all`, {
        method: "PATCH",
    });

    if(!response.ok) {
        throw await parseError(
            response,
            "Failed to mark notifications as read",
        );
    }

    return response.json()
}