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
        <div className="flex items-start justify-between gap-4">
            <div>
                <ServiceDeliveryPageTitle title="Engagements" />
                <p className="mt-2 text-sm text-brand-text/80">
                    Claim requests, coordinate scope and quote, assign specialists, schedule testing, and review delivery.
                </p>
            </div> 
            <Button variant="outline" className={whiteOutlineButtonClass} onClick={clearFilters}>Clear Filters</Button>
        </div>   

        <Card className="mt-6 border-brand-panel-border bg-brand-panel">
        <CardContent>
            <div className="flex flex-wrap gap-3">
                <Input
                    placeholder="Search engagements..."
                    value={search}
                    onChange={(e)=> setSearch(e.target.value)}
                    className={cn("min-w-[240px] flex-1", controlFieldClass)}
                />
                <Select value={status} onValueChange={(v) => setStatus(v as EngagementStatus | "all")}>
                    <SelectTrigger className={cn("w-[170px]",controlFieldClass)}><SelectValue placeholder="All statuses"/></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All statuses</SelectItem>
                        {STATUS_OPTIONS.map((s) => (
                            <SelectItem key={s} value ={s}>{statusLabels[s]}</SelectItem>
                        ))}
                    </SelectContent>
                <Select value={assessmentType} onValueChange={(v) => setAssessmentType(v as AssessmentType | "all")}>
                    <SelectTrigger className={cn("w-[190px]", controlFieldClass)}><SelectValue placeholder="All assessments" /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All assessments</SelectItem>
                        {ASSESSMENT_OPTIONS.map((a) => (
                            <SelectItem key={a} value={a}>{assessmentTypeLabels[a]}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                    <Select value={assignment} onValueChange={(v) => setAssignment(v as AssignmentFilter)}>
                        <SelectTrigger className={cn("w-[170px]", controlFieldClass)}><SelectValue placeholder="All assignments" /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All assignments</SelectItem>
                            <SelectItem value="assigned">Assigned</SelectItem>
                            <SelectItem value="unassigned">Unassigned</SelectItem>
                        </SelectContent>
                        </Select>
                </Select>
            </div>

        </CardContent>

        </Card>

        
    </>
    )


}