"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

import ServiceDeliveryPageTitle from "@/shared/components/ServiceDeliveryPageTitle";
import ServiceDeliveryModal from "@/shared/components/ServiceDeliveryModal";
import FindingInspectModal from "@/shared/components/FindingInspectModal";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import {
    assignPentester,
    cancelEngagement,
    claimEngagement,
    completeEngagementReview,
    downloadEvidence,
    getEngagementDetail,
    getEngagementFinding,
    listEngagementFindings,
    listEngagementRetests,
    listAuditActivity,
    listPentesters,
    reassignEngagement,
    rescheduleEngagement,
    returnEngagementFromReview,
    scheduleEngagement,
    updateEngagementScoping,
} from "@/lib/serviceDeliveryService";
import type {
    Activity,
    EngagementActionResponse,
    EngagementDetail,
    EngagementStatus,
    FindingDetail,
    FindingListItem,
    PentesterListItem,
    Retest,
} from "@/lib/serviceDeliveryTypes";
import {
    assessmentTypeLabels,
    controlFieldClass,
    displayName,
    downloadBlob,
    downloadTextFile,
    formatCurrency,
    formatDate,
    formatDateRange,
    formatDateTime,
    formatLabel,
    retestStatusPillClass,
    severityClass,
    statusLabels,
    statusPillClass,
    whiteOutlineButtonClass,
} from "@/lib/serviceDeliveryUi";

const STATE_DESCRIPTIONS: Record<EngagementStatus, string> = {
    requested: "New request awaiting Service Delivery ownership. Claiming it moves the engagement into Scoping.",
    scoping: "Commercial and delivery details are being confirmed. Scope, final quote, pentester, and dates can still be changed.",
    scheduled: "Scope and commercial details are locked. Schedule and pentester changes are exceptional and require a reason.",
    in_progress: "Testing has started. Scope, quote, pentester, and schedule are locked; Service Delivery coordinates and monitors only.",
    review: "Pentester has submitted the engagement. Delivery configuration is locked while Service Delivery performs final quality review.",
    completed:"Engagment is complete and read-only. ",
    cancelled: "Engagement was cancelled and is read-only",
};