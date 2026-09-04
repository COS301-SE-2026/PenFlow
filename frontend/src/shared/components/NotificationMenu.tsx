"use client";

import { Bell, CheckCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

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
        <div className="relative">
            <button type="button"
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
                <div className="absolute left-full top-0 z-[100] ml-3 w-96 rounded-xl border border-brand-panel-border bg-brand-panel shadow-xl">
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
                            <p className="p-4 text-sm text-muted-foreground">
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
                                        notification.is_read ? "opacity-60" : "bg-brand-cyan/5"
                                    }`}
                                >

                                    <span className="font-semibold">
                                        {notification.title}
                                    </span>

                                    <span className="mt-1 block text-sm text-muted-foreground">
                                        {notification.message}
                                    </span>

                                    <time className="mt-2 block text-xs text-muted-foreground">
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