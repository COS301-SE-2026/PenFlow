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
import { add_domain, delete_domain, fetch_domain, verify_domain, verification_code_message,
    type domain_counts,
    type domain_item,
    type domain_pagination,
    type domain_sort_field,
    type domain_verification_status,
    type sort_order,
 } from "@/lib/domainService";
import { Button } from "@/shared/components/ui/button";

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
 };
 
 function format_timestamp(iso: string): string {
   return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
   });
 }

 function StatusBadge({ status }: {status: domain_verification_status}) {
   const { label, className, icon:Icon} = status_config[status];
   return (
      <Badge variant = "outline" className={cn("gap-1 uppercase tracking-wide", className)}>
         <Icon className = "size-3" />
         {label}
      </Badge>
   );
 }

 function CopyField({label, value}:{label: string; value: string }) { 
   const [copied, set_copied] = useState(false);

   async function handle_copy() {
      try {
         await navigator.clipboard.writeText(value);
         set_copied(true);
         setTimeout(() => set_copied(false), 1500);
      } catch {}
   }

   return (
      <div className = "flex flex-col gap-1">
         <span className = "text-xs text-muted-foreground">{label}</span>
         <div className = "flex items-center gap-2 rounded-lg border border-brand-panel-border bg-brand-panel-deep px-3 py-2">
            <code className = "min-w-0 flex-1 truncate font-mono text-sm text-foreground">{value}</code>
            <button
               type = "button"
               onClick={handle_copy}
               aria-label = {`Copy ${label}`}
               className = "shrink-0 text-muted-foreground transition-colors hover:text-brand-cyan">
                  {copied ? <Check className = "size-4 text-brand-success" /> : <Copy className = "size-4" />}
               </button>
         </div>
      </div>
   );
 }

 function VerificationStep ({ index, title, children }: {index: number; title: string; children: React.ReactNode}) {
   return (
      <div className = "flex gap-3">
         <span className = "flex size-5 shrink-0 items-center justify-center rounded-full bg-brand-cyan/15 text-xs font-semibold text-brand-cyan">
            {index}
         </span>
         <div className = "flex min-w-0 flex-1 flex-col gap-2">
            <p className = " text-sm font-medium text-foreground"> {title} </p> {children}
         </div>
      </div>
   );
 }

 function DomainDetailPanel ({
   domain, on_close, on_verify, on_delete, verifying
 }: {
   domain:domain_item;
   on_close: () => void;
   on_verify: (id: string) => void;
   on_delete: (id:string) => void;
   verifying: boolean;
 }) {
   const { label, className, icon: Icon } = status_config[domain.status];
   const status_message = domain.last_verification_code ? verification_code_message[domian.last_verification_code]
   : "This domain has not been checked yet.";

   return (
      <Card className = "border border-brand-panel-border bg-brand-panel ring-0">
         <CardContent className = "flex flex-col gap-5">
            <div className = "flex items-start justify-between gap-3">
               <div className = "flex items-center gap-2.5">
                  <Globe className = "size-5 text-brand-cyan" />
                  <h2 className = "truncate text-lg font-semibold text-foreground">{domain.domain}</h2>
               </div>
               <button
                  type = "button"
                  onClick = {on_close}
                  aria-label = "Close domain details"
                  className = "shrink-0 text-muted-foreground transition-colors hover:text-foreground"
                  >
                     <X className = "size-5"/>
                  </button>
            </div>

            <Badge variant "outline" className={cn ("w-fit gap-1 uppercase tracking-wide", className)}>
               <Icon className = "size-3" />
               {label} verification 
            </Badge>

            <Separator className = "bg-brand-panel-border" />

            <div>
               <h3 className = "mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Domain details
               </h3>
               <div className = "grid grid-cols-2 gap-x-4 gap-y-3">
                  <div>
                     <p className ="text-xs text-muted-foreground"> Added on</p>
                     <p className ="text-sm text-foreground">{format_timestamp(domain.created_at)}</p>
                  </div>
                  <div>
                     <p className ="text-xs text-muted-foreground"> Last checked</p>
                     <p className ="text-sm text-foreground">{format_timestamp(domain.last_checked_at) : "Never"}</p>
                  </div>
               </div>
            </div>

            {domain.status !== "verified" && (
               <>
                  <Separator className = "bg-brand-panel-border"/>
                  <div className = "flex flex-col gap-4">
                     <div>
                        <h3 className = "text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                           Verify ownership
                        </h3>
                        <p className ="mt-1 text-sm text-muted-foreground">
                           To enable active scans, add the following DNS TXT record to your domain &apos;s root.
                           </p>
                     </div>

                     <VerificationStep index = {1} title = "add this DNS TXT record">
                        <CopyField label = "TXT Record Value" value={domain.verification_token} />
                     </VerificationStep>

                     <VerificationStep index = {2} title = "Wait for DNS propagation">
                        <p className ="mt-1 text-sm text-muted-foreground">
                           DNS changes can take up to 24 hours to propagate worldwide.
                           </p>
                     </VerificationStep>

                     <VerificationStep index = {3} title = "Verify ownership">
                        <p className ="mt-1 text-sm text-muted-foreground">
                           We will check for the record and confirm your ownership.
                           </p>
                     </VerificationStep>
                  </div>

                  <div className = " flex flex-col gap-3">
                     <h3 className = "text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Current status
                     </h3>
                     <div className = "flex gap-3 rounded-lg border border-brand-alert/25 bg-brand-alert/5 p-3">
                     <AlertTriangle className = "size-4 shrink-0 text-brand-alert" />
                     <div>
                        <p className ="text-sm font-medium text-foreground"> {status_message}</p>
                        <p className ="mt-0.5 text-xs text-muted-foreground">
                           {domain.last_checked_at
                              ? `Last checked ${format_timestamp(domain.last_checked_at)}.`
                              : "this domain hasn't been checked yet."
                           }
                        </p>
                     </div>
                  </div>
               </>
               <Button
                  
            )}
         </CardContent>
      </Card>
   )


 }