"use client"

import { useEffect, useState } from "react";

import ServiceDeliveryPageTitle from "@/shared/components/ServiceDeliveryPageTitle";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { listAuditActivity } from "@/lib/serviceDeliveryService";
import type { Activity } from "@/lib/serviceDeliveryTypes";
import { controlFieldClass, displayName, formatDateTime, formatLabel } from "@/lib/serviceDeliveryUi";

export default function ServiceDeliveryAuditPage(){
    const [logs, setLogs] = useState<Activity[]>([]);
    const [search, setSearch] = useState("");
    const [entityType, setEntityType] = useState<string>("all");

    useEffect(()=> {
        listAuditActivity({ limit: 200}).then((res) => setLogs(res.items)).catch(console.error);
    }, [])

    const entityTypes = Array.from(new Set(logs.map((log) => log.entity_type))).sort((a, b) => a.localeCompare(b));

    const filtered = logs.filter((log) => {
        const query = search.trim().toLowerCase();
        const matchesQuery =
            !query ||
            displayName(log.actor,"").toLowerCase().includes(query) ||
            log.action.toLowerCase().includes(query) ||
            log.entity_type.toLowerCase().includes(query);
        const matchesType =entityType ==="all"||log.entity_type===entityType;
        return matchesQuery&& matchesType;
    });

    return (
        <>
        <ServiceDeliveryPageTitle title="Audit logs" />
        <p className="mt-2 text-sm text-brand-text/80">Read-only operational history for engagements managed through Service Delivery.</p>

        <Card className="mt-6 border-brand-panel-border bg-brand-panel">
            <CardContent>
            <div className="flex flex-wrap gap-3">
                <Input
                    placeholder="Search engagement activity..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className={cn("min-w-[240px] flex-1", controlFieldClass)}
                />
                <Select value={entityType} onValueChange={setEntityType}>
                    <SelectTrigger className={cn("w-[190px]", controlFieldClass)}><SelectValue placeholder="All entity types" /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All entity types</SelectItem>
                            {entityTypes.map((t) => (
                                <SelectItem key={t} value={t} className="capitalize">{formatLabel(t)}</SelectItem>
                                ))}
                    </SelectContent>
                </Select>
           </div>

           <div className="mt-6 overflow-x-auto">
                <Table>
                    <TableHeader>
                        <TableRow>
                                <TableHead>Time</TableHead>
                                <TableHead>Actor</TableHead>
                                <TableHead>Action</TableHead>
                                <TableHead>Entity</TableHead>
                        </TableRow>           
                    </TableHeader>
                    <TableBody>
                                {filtered.length === 0 ? (
                                 <TableRow><TableCell colSpan={4} className="text-brand-text/70">No activity matches these filters.</TableCell></TableRow>
                                ):(
                                    filtered.map((log)=> (
                                        <TableRow key={log.id}>
                                        <TableCell>{formatDateTime(log.created_at)}</TableCell>
                                        <TableCell>{displayName(log.actor, "System")}</TableCell>
                                        <TableCell className="font-mono text-xs">{log.action}</TableCell>
                                        <TableCell className="capitalize">{formatLabel(log.entity_type)}</TableCell>
                                        </TableRow>
                                    ))
                                )}

                    </TableBody>

                </Table>
                                

           </div>











            </CardContent>
        </Card>
        </>
    );

}

    

