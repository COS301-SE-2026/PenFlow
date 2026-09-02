"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import ServiceDeliveryPageTitle from "@/shared/components/ServiceDeliveryPageTitle";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { listEngagements } from "@/lib/serviceDeliveryService";
import type { AssessmentType, EngagementListItem, EngagementStatus } from "@/lib/serviceDeliveryTypes";
import { assessmentTypeLabels, controlFieldClass, displayName, formatDateRange, statusLabels, statusPillClass, whiteOutlineButtonClass } from "@/lib/serviceDeliveryUi";

const STATUS_OPTIONS:EngagementStatus[]= ["requested", "scoping", "scheduled", "in_progress", "review", "completed", "cancelled"];
const ASSESSMENT_OPTIONS:AssessmentType[]= ["web_application", "mobile_application", "api", "network", "cloud", "other"];

type AssignmentFilter = "all" | "assigned" | "unassigned";

export default function ServiceDeliveryEngagementsPage() {
    return(
        <Suspense fallback={null}>
            <ServiceDeliveryEngagementsPageInner />
        </Suspense>
    )
}

function ServiceDeliveryEngagementsPageInner(){
    const searchParams =useSearchParams();
    const [engagements, setEngagements] =useState<EngagementListItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [status, setStatus] = useState<EngagementStatus | "all">((searchParams.get("status") as EngagementStatus) || "all");
    const [assessmentType, setAssessmentType] = useState<AssessmentType | "all">("all");
    const [assignment, setAssignment] = useState<AssignmentFilter>("all");

    useEffect(() => {
        setIsLoading(true);
        listEngagements({
            search: search || undefined,
            status: status === "all" ? undefined : status,
            assessment_type: assessmentType === "all" ? undefined : assessmentType,
            assigned: assignment === "all" ? undefined : assignment === "assigned", 

        })
            .then((res) =>setEngagements(res.items))
            .catch(console.error)
            .finally(() => setIsLoading(false));
    },[search, status, assessmentType, assignment])

     function clearFilters() {
        setSearch("");
        setStatus("all");
        setAssessmentType("all");
        setAssignment("all");
    }

    return(
    <>    
    </>
    )


}