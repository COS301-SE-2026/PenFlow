"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link"
import { AlertTriangle, Check, CheckCircle2, ChevronDown, ChevronRight, Clock, Copy, Globe, MoreVertical, Plus,
    Search, Trash2, X, XCircle,
} from "lucide-react";

import type {LucideIcon} from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { add_domain, delete_domain, fetch_domain, verify_domain, verification_code_Message,
    type domain_counts,
    type domain_item,
    type domain_pagination,
    type domain_sort_field,
    type domain_verification_status,
    type sort_order,
 } from "@/lib/domainService";

 const PAGE_SIZE = 20;
 const sort_options = { value: string; label: string; sort: domain_sort_field; order: sort_order }[] = [
    {value: "recent", label: "Sort: Recently Added", sort: "created_at", order: "desc" },
    {value: "az", label: "Sort: A - Z", sort: "domain", order: "asc" },
    {value: "status", label: "Sort: Status", sort: "status", order: "asc" },

 ];

 const tab_defs: { key: "all" | domain_verification_status; label: string } [] = [
    { key: "all", label: "All Domains"},
    { key: "verified", label: "Verified"},
    { key: "pending", label: "Pending"},
    { key: "failed", label: "Failed"},
    { key: "expired", label: "Expired"},
 ];

 const status_config: Record<domain_verification_status, { label: string; className: string; icon: LucideIcon}> = {
    verified: {label: "Verified", className: "border-brand-success text-brand-success bg-brand-success/10", icon: CheckCircle2 },
    pending: {label: "Pending", className: "border-brand-yellow text-brand-yellow bg-brand-yellow/10", icon: Clock },
    failed: {label: "Failed", className: "border-brand-alert text-brand-alert bg-brand-alert/10", icon: XCircle },
    expired: {label: "Expired", className: "border-brand-orange text-brand-orange bg-brand-orange/10", icon: AlertTriangle },
 }
 