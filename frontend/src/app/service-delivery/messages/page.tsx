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

}