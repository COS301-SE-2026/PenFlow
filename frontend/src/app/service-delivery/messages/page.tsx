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
    

}