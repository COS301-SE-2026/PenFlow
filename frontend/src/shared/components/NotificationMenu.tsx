"use client";

import { Bell, CheckCheck } from "lucide-react";
import {
    useCallback,
    useEffect,
    useId,
    useRef,
    useState,
} from "react";

import {
    fetchNotifications,
    markAllNotificationsRead,
    markNotificationRead,
    type NotificationItem,
} from "@/lib/notificationService";

export default function NotificationMenu() {
    const [notifications, setNotifications] = useState<NotificationItem[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);

    const containerRef = useRef<HTMLDivElement>(null);
    const triggerRef = useRef<HTMLButtonElement>(null);
    const panelId = useId();

    useEffect(() => {
        if (!open) return;

        function handleOutsidePointer(event: PointerEvent) {
            if (
                event.target instanceof Node &&
                !containerRef.current?.contains(event.target)
            ) {
                setOpen(false);
            }
        }

        function handleKeyDown(event: KeyboardEvent) {
            if (event.key === "Escape") {
                setOpen(false);
                triggerRef.current?.focus();
            }
        }

        document.addEventListener(
            "pointerdown",
            handleOutsidePointer,
            true,
        );
        document.addEventListener("keydown", handleKeyDown);

        return () => {
            document.removeEventListener(
                "pointerdown",
                handleOutsidePointer,
                true,
            );
            document.removeEventListener("keydown", handleKeyDown);
        };
    }, [open]);

    const refresh = useCallback(async () => {
        try {
            const result = await fetchNotifications({unreadOnly: false, limit: 10});
            setNotifications(result.items);
            setUnreadCount(result.unread_count);
        } catch (error) {
            console.error("Failed to load notifications", error);
        }
    }, []);

    useEffect(() => {
        void refresh();

        const interval = window.setInterval(() => {
            if(document.visibilityState == "visible") {
                void refresh();
            }
        }, 30_000);

        return () => window.clearInterval(interval);
    }, [refresh]);

    async function handleNotificationClick(notification: NotificationItem) {
        if(!notification.is_read) {
            await markNotificationRead(notification.id);

            setNotifications((current) =>
                current.map((item) =>
                    item.id == notification.id
                    ? {...item, is_read:true}
                    : item,
                ),
            );

            setUnreadCount((count) => Math.max(0, count-1));
        }
        //Navigation of specific notifications possible here
    }

    async function handleMarkAllRead() {
        setLoading(true);

        try {
            await markAllNotificationsRead();
            setNotifications((current) => 
                current.map((item) => ({...item, is_read:true})),
            );
            setUnreadCount(0);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div ref={containerRef} className="relative">
            <button type="button"
                ref={triggerRef}
                aria-expanded={open}
                aria-controls={open ? panelId : undefined}
                aria-label="View notifications"
                onClick={() => {
                    setOpen((current) => !current);
                    void refresh();
                }}
                className="nav-link flex w-full items-center px-3 py-2 text-left">

                <span className="relative inline-flex">
                    <Bell className="size-5" />

                    {unreadCount > 0 && (
                    <span className="absolute -right-2 -top-2 rounded-full bg-red-500 px-1.5 text-xs text-white">
                        {unreadCount > 99 ? "99+": unreadCount}
                    </span>
                )}
                </span>
            </button>

            {open && (
                <div id={panelId} className="absolute left-full top-0 z-[100] ml-3 w-96 rounded-xl border border-brand-panel-border bg-brand-panel text-slate-100 shadow-xl">
                    <div className="flex items-center justify-between border-b border-brand-panel-border p-4">
                        <h2>Notifications</h2>

                        <button
                            type="button"
                            disabled={loading || unreadCount == 0}
                            onClick={() => void handleMarkAllRead()}
                        >

                            <CheckCheck className="size-4" />
                            Mark all read
                        </button>
                    </div>

                    <div className="max-h-96 overflow-y-auto">
                        {notifications.length === 0 ? (
                            <p className="p-4 text-sm text-slate-300">
                                No notifications yet.
                            </p>
                        ) : (
                            notifications.map((notification) => (
                                <button 
                                    key={notification.id}
                                    type="button"
                                    onClick={() =>
                                        void handleNotificationClick(notification)
                                    }
                                    className={`block w-full border-b border-brand-panel-border p-4 text-left ${
                                        notification.is_read
                                            ? "bg-transparent hover:bg-white/5"
                                            : "bg-blue-400/10 hover:bg-blue-400/15"
                                    }`}
                                >

                                    <span className="font-semibold text-slate-100">
                                        {notification.title}
                                    </span>

                                    <span className="mt-1 block text-sm leading-relaxed text-slate-300">
                                        {notification.message}
                                    </span>

                                    <time className="mt-2 block text-xs text-slate-400">
                                        {new Date(notification.created_at).toLocaleDateString()}
                                    </time>
                                </button>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}