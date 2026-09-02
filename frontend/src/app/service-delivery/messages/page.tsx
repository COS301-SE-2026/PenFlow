"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import ServiceDeliveryPageTitle from "@/shared/components/ServiceDeliveryPageTitle";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { getEngagementDetail, listConversationMessages, listConversations, markConversationRead, sendConversationMessage } from "@/lib/serviceDeliveryService";
import type { Conversation, EngagementMessage, EngagementMessageChannel } from "@/lib/serviceDeliveryTypes";
import { controlFieldClass, displayName, formatDateTime } from "@/lib/serviceDeliveryUi";


const CHANNEL_LABELS: Record<EngagementMessageChannel, string> = {
    client_service_delivery: "Client",
    service_delivery_pentester: "Pentester",
};

const CHANNEL_ROLE_CLASS: Record<EngagementMessageChannel, string> = {
    client_service_delivery: "text-brand-cyan",
    service_delivery_pentester: "text-brand-orange",
};

function conversationKey(engagementId: string, channel: EngagementMessageChannel): string {
    return `${engagementId}::${channel}`;
}

interface ActiveThread {
    engagementId: string;
    channel: EngagementMessageChannel;
    engagementTitle: string;
    participantName: string;
    participantRole: string;
}

export default function MessagesPage() {
    return (
        <Suspense fallback={null}>
            <MessagesPageInner />
        </Suspense>
    );
}

function MessagesPageInner() {
 const searchParams = useSearchParams();
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [search, setSearch] = useState("");
    const [activeKey, setActiveKey] = useState<string | null>(() => {
        const engagement = searchParams.get("engagement");
        const channel = searchParams.get("channel") as EngagementMessageChannel | null;
        return engagement && channel ? conversationKey(engagement, channel) : null;
    });
    const [fallbackThread, setFallbackThread] = useState<ActiveThread | null>(null);
    const [messages, setMessages] = useState<EngagementMessage[]>([]);
    const [draft, setDraft] = useState("");

    const loadConversations = () => {
        listConversations().then((res) => {
            setConversations(res.items);
            if (!activeKey && res.items.length > 0) {
                setActiveKey(conversationKey(res.items[0].engagement_id, res.items[0].channel));
            }
        }).catch(console.error);
    };

    useEffect(loadConversations, []); 

    const activeConversation = conversations.find(
        (c) => activeKey === conversationKey(c.engagement_id, c.channel),
    ) ?? null;

    // messages only returns conversations that already have at least one add a way so the can enter chat box
    useEffect(() => {
        if (!activeKey || activeConversation) {
            setFallbackThread(null);
            return;
        }
        const [engagementId, channel] = activeKey.split("::") as [string, EngagementMessageChannel];
        getEngagementDetail(engagementId).then((detail) => {
            const participant = channel === "client_service_delivery" ? detail.client : detail.assigned_pentester;
            if (!participant) return; // pentester channel requested before one is assigned
            setFallbackThread({
                engagementId,
                channel,
                engagementTitle: detail.title,
                participantName: displayName(participant),
                participantRole: CHANNEL_LABELS[channel],
            });
        }).catch(console.error);
    }, [activeKey, !!activeConversation]);

    const activeThread: ActiveThread | null = activeConversation
        ? {
            engagementId: activeConversation.engagement_id,
            channel: activeConversation.channel,
            engagementTitle: activeConversation.engagement_title,
            participantName: activeConversation.participant.full_name ?? activeConversation.participant.email,
            participantRole: CHANNEL_LABELS[activeConversation.channel],
        }
        : fallbackThread;

          useEffect(() => {
        if (!activeThread) {
            setMessages([]);
            return;
        }
        listConversationMessages(activeThread.engagementId, activeThread.channel)
            .then((res) => setMessages(res.items))
            .then(() => markConversationRead(activeThread.engagementId, activeThread.channel))
            .then(loadConversations)
            .catch(console.error);
    }, [activeThread?.engagementId, activeThread?.channel]);

    const filteredConversations = conversations
        .filter((c) => !search || c.engagement_title.toLowerCase().includes(search.toLowerCase()))
        .sort((a, b) => (b.last_message?.created_at ?? "").localeCompare(a.last_message?.created_at ?? ""));

    async function handleSend() {
        if (!draft.trim() || !activeThread) return;
        await sendConversationMessage(activeThread.engagementId, { comment: draft.trim(), channel: activeThread.channel });
        const updated = await listConversationMessages(activeThread.engagementId, activeThread.channel);
        setMessages(updated.items);
        setDraft("");
        loadConversations();
    }
    

 return (
        <>
            <ServiceDeliveryPageTitle title="Messages" />
            <p className="mt-2 text-sm text-brand-text/80">One row per conversation - client and pentester threads are kept separate.</p>

            <Card className="mt-6 border-brand-panel-border bg-brand-panel">
                <CardContent className="grid grid-cols-1 gap-0 p-0 md:grid-cols-[320px_1fr]">
                    <aside className="border-b border-brand-panel-border p-4 md:border-r md:border-b-0">
                        <Input placeholder="Search conversations..." value={search} onChange={(e) => setSearch(e.target.value)} className={cn("mb-3", controlFieldClass)} />
                        <div className="space-y-1">
                            {filteredConversations.map((c) => {
                                const key = conversationKey(c.engagement_id, c.channel);
                                return (
                                    <button
                                        key={key}
                                        onClick={() => setActiveKey(key)}
                                        className={cn(
                                            "block w-full rounded-md border border-transparent p-3 text-left text-sm hover:bg-white/5",
                                            activeKey === key && "border-brand-cyan/40 bg-white/5",
                                        )}
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="font-semibold text-brand-text">{c.engagement_title}</div>
                                            {c.unread_count > 0 && (
                                                <span className="shrink-0 rounded-full bg-brand-cyan px-1.5 py-0.5 text-[10px] font-semibold text-black">{c.unread_count}</span>
                                            )}
                                        </div>
                                        <div className="text-xs text-brand-text/70">
                                            {c.participant.full_name ?? c.participant.email} · <span className={cn("font-semibold", CHANNEL_ROLE_CLASS[c.channel])}>{CHANNEL_LABELS[c.channel]}</span>
                                        </div>
                                        <div className="mt-1 truncate text-[11px] text-brand-text/70">
                                            {c.last_message ? c.last_message.comment : "No messages yet"}
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </aside>

                    <div className="flex min-h-[500px] flex-col">
                        {!activeThread ? (
                            <p className="p-6 text-sm text-brand-text/70">Select a conversation.</p>
                        ) : (
                            <>
                                <div className="border-b border-brand-panel-border p-4">
                                    <div className={cn("text-xs font-semibold tracking-wide uppercase", CHANNEL_ROLE_CLASS[activeThread.channel])}>{activeThread.participantRole}</div>
                                    <div className="text-sm font-semibold text-brand-text">{activeThread.engagementTitle}</div>
                                    <div className="text-xs text-brand-text/70">with {activeThread.participantName}</div>
                                </div>

                                <div className="flex-1 space-y-2 overflow-y-auto p-4">
                                    {messages.length === 0 ? (
                                        <p className="text-sm text-brand-text/70">No messages in this channel yet.</p>
                                    ) : (
                                        messages.map((m) => (
                                            <div
                                                key={m.id}
                                                className={cn(
                                                    "max-w-[72%] rounded-md border border-white/15 bg-white/[0.06] p-3",
                                                    m.user.role === "service_delivery" && "ml-auto border-brand-blue/40 bg-brand-blue/20",
                                                )}
                                            >
                                                <div className="flex justify-between gap-3 text-xs text-brand-text/70">
                                                    <b className="text-brand-text">{displayName(m.user)}</b>
                                                    <span>{formatDateTime(m.created_at)}</span>
                                                </div>
                                                <p className="mt-1.5 text-sm text-brand-text/90">{m.comment}</p>
                                            </div>
                                        ))
                                    )}
                                </div>

                                <div className="grid grid-cols-[1fr_auto] gap-2 border-t border-brand-panel-border p-4">
                                    <textarea
                                        value={draft}
                                        onChange={(e) => setDraft(e.target.value)}
                                        placeholder={`Message ${activeThread.participantName}...`}
                                        className="h-16 resize-none rounded-md border border-brand-panel-border bg-transparent p-2 text-sm text-brand-text outline-none"
                                    />
                                    <Button onClick={handleSend} disabled={!draft.trim()}>Send</Button>
                                </div>
                            </>
                        )}
                    </div>
                </CardContent>
            </Card>
        </>
    );
}

