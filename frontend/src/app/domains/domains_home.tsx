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
import { Separator } from "@/shared/components/ui/separator";
import nextConfig from "next.config";

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
               <Button
                  variant = "outline"
                  className ="border-brand-yellow text-brand-yellow hover:bg-brand-yellow/10"
                  disabled = {verifying}
                  onClick={() => on_verify(domain.id)}
               >
                  {verifying ? "Verifying..." : "Verify now"}
               </Button>
            </div>
         </>
      )}

      <Separator className = "bg-brand-panel-border" />
      <div className = "flex flex-col gap-1">
         <h3 className = "mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            More actions
         </h3>
         <button
            type = "button"
            onClick={() => on_delete(domain.id)}
            className = "flex items-center gap-2 rounded-md px-1 py-2 text-left text-sm text-brand-alert transition-colors hover:text-brand-alert/80">
            <Trash2 className = "size-4" />
            Remove domain
         </button>
      </div>
   </CardContent>
</Card>
);}


function AddDomainForm({
   on_cancel,
   on_added,
}: {
   on_cancel: () => void;
   on_added: () => void;
}) {
const [domain_name, set_domain_name] = useState("");
const [submiting, set_submitting] = useState(false);
const [form_error, set_form_error] = useState<string | null>(null);
const can_add = domain_name.trim() !== "" && !submitting

async function handle_add() {
   if (!can_add) return;
   set_submitting(true);
   set_form_error(null);
   try {
      await add_domain(domain_name.trim());
      on_added();
   } catch (err) {
      set_form_error(err instanceof Error ? err.message : "Failed to add domain");
   } finally {
      set_submitting(false);
   }
}

return (
   <Card className = "border border-brand-cyan/30 bg-gradient-to-br from-brand-panel to-brand-panel-deep ring-0">
      <CardContent className = "flex flex-col gap-4">
         <div className = "flex items-center gap-2.5">
            <span className = "flex size-8 items-center justify-center rounded-lg border border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan">
               <Globe className = "size-4"/>
            </span>
            <div>
               <h2 className = "text-sm font-semibold uppercase tracking-wide text-foreground">Add Domain</h2>
               <p className = "text-xs text-muted-foreground">
                  Start passive monitoring immediately - active scans available once domain is verified.
               </p>
            </div>
         </div>

         <Separator className = "bg-brand-panel-border"/>
         <div className = "flex flex-col gap-1.5">
            <Label htmlFor="new-domain">Domain</Label>
            <div className = "relative">
               <Glove className = "absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"/>
               <Input
                  id = "new-domain"
                  placeholder="example.com"
                  value={domain_name}
                  onChange = {(e) => set_domain_name(e.target.value)}
                  onKeyDown = {(e) => {
                     if (e.key === "Enter") void handle_add();
                  }}
                  className = "h-10 border-brand-cyan/60 pl-6 focus-visible:border-brand-cyan focus-bisible:ring-brand-cyan/25"
                  autoFocus
               />
            </div>
            {form_error && <p className = "text-sx text-brand-alert">{form_error}</p>}
            <p className = "text-xs text-muted-foreground">
               You will need to verify ownership via a DNS TXT record before active scans are available for this domain.
            </p>
         </div>

         <div className = "flex justify-end gap-2">
            <Button variant = "outline" onClick={on_cancel} disable={submiting}>
               Cancel
            </Button>
            <Button disabled={!can_add} onClick={() => void handle_add()}>
               {submitting ? "Adding" : "Add Domain"}
               </Button> 
         </div>
      </CardContent>
   </Card>
);}

function useDomains() {
   const [domains, set_domains] = useState<domain_item[]>([]);
   const [counts, set_counts] = useState<domain_counts | null>(null);
   const [pagination, set_pagination] = useState<domain_pagination| null>(null);
   const [loading, set_loading] = useState(false);
   const [error, set_error] = useState<string | null>(null);

   const [active_tab, set_active_tab] = useState<"all" | domain_verification_status>("all");
   const [search, set_search] = useState("");
   const [debounced_search, set_debounced_search] = useState("");
   const [sort_value, set_sort_value] = useState("recent");
   const [verifying_id, set_verifying_id] = useState<string | null>(null);

   const request_id_ref = useRef(0);

   useEffect(()=>{
      const handle = setTimeout (() => set_debounced_search(search.trim()), 350);
      return () => clearTimeout(handle);
   }, [search]);

   const load_domains = useCallback(
      async (params: { offset: number; append: boolean}) => {
         const request_id = ++request_id_ref.current;
         set_loading(true);
         set_error(null);
         const option = sort_options.find((o) => o.value === sort_value) ?? sort_options[0];
         try{
            const result = await fetch_domains({
               status: active_tab === "all" ?undefined : active_tab,
               search: debounced_search || undefined,
               sort: option.sort,
               order: option.order,
               limit: PAGE_SIZE,
               offset: params.offset,
            });
            if (request_id_ref.current !== request_id) return;
            set_domains((prev) => (params.append ? [...prev, ...result.items] : result.items));
            set_counts(result.counts);
            set_pagination(result.pagination);
         }
         catch (err) {
            if (request_id_ref.current !== request_id) return;
            set_error(err instanceof Error ? err.message : "Failed to load domains");
         }
         finally {
            if (request_id_ref.current === request_id) set_loading(false);
         }
      },
      [active_tab, debounced_search, sort_value]
   );

   const refetch = useCallback (() => load_domains({offset:0, append: false}), [load_domains]);

   useEffect(() => {
      void refetch();
   }, [refetch]);

   function handle_load_more() {
      if (!pagination?.has_more || loading) return;
      void load_domains ({ offset: domains.length, append: true});
   }

   async function verify(domain_id: string) {
      set_verifying_id(domain_id);
      try { 
         await verify_domain(domain_id);
      } catch {

      } finally {
         set_verifying_id(null);
         void refetch();
      }
   }

   async function remove(domain_id: string): Promise<boolean> {
      try {
         await delete_domain(domain_id);
         void refetch();
         return true;
      } catch(err) {
         set_error(err instanceof Error ? err.message: "Failed to remove domain");
         return false;
      }
   }

   return{ domains, counts, pagination, loading, error, active_tab, set_active_tab, search, set_search, sort_value, set_sort_value, verifying_id, refetch, handle_load_more, verify, remove,};
}

export default function DomainsHome() {
   const {
      domains, counts, pagination, loading, error, active_tab, set_active_tab, search, set_search, sort_value, set_sort_value, verifying_id, refetch, handle_load_more, verify, remove,
   } = useDomains();

   const [selected_id, set_selected_id] = useState<string | null>(null);
   const [show_add_domain, set_show_add_domain] = useState(false);

   async function handle_delete(domain_id: string) {
      const deleted = await remove(domain_id);
      if(deleted) set_selected_id((prev) => (prev === domain_id ? null : prev));
   }

   const selected_domain = domains.find((d) => d.id === selected_id ?? null);

   return(
      <div className = "flex flex-col gap-6">
         <nav aria-label = "Breadcrumb" className = "flex items-center gap-1 text-sm text-muted-foreground">
            <Link href = "/dashboard" className = "hover:text-foreground hover:underline">
               Home
            </Link>
            <ChevronRight className = "size-4"/>
            <span className = "text-foreground">Domains</span>
         </nav>

         <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
               <h1 className="text-2xl font-semibold text-foreground">Domains</h1>
               <p className="mt-1 text-sm text-muted-foreground">
                  Manage verified domains and control which domains can recieve active scans.
               </p>
            </div>
            <Button
               onClick={() => set_show_add_domain((prev) => !prev)}
               aria-pressed={show_add_domain}
               className="gap-1.5 trasition-all duration-200 hover:-translate-y-0.5
                          hover:bg-primary/85 hover:shadow-[0_0_20px_rgba(43.216.245.0.45)]"
            >
               <Plus className="size-4"/>
               Add Domain
            </Button>
         </div>

         {show_add_domain && (
            <AddDomainForm
               on_cancel={() => set_show_add_domain(false)}
               on_added={() => {
                  set_show_add_domain(false);
                  void refetch();
               }}
            />
         )}
         <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
            <div className = "flex min-w-0 flex-col gap-4 lg:flex-1">
               <div className="flex flex-wrap items-center gap-2 border-b border-brand-panel-border">
                  {tab_defs.map((tab) => (
                     <button
                        key={tab.key}
                        type="button"
                        onClick = {() => set_active_tab(tab.key)}
                        className = {cn (
                           "flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors",
                           active_tab === tab.key
                              ? "border-brand-cyan text-foreground"
                              : "border-transparent text-muted-foreground hover:text-foreground"
                        )}
                     >
                        {tab.label}
                        <span
                           className={cn(
                              "flex size-5 items-center justify-center rounded-full text-xs",
                              active_tab === tab.key 
                                 ? "bg-brand-cyan/15 text-brand-cyan"
                                 : "bg-muted text-muted-foreground"
                           )}
                        >
                           {counts?.[tab.key] ?? 0}
                        </span>
                     </button>
                  ))}
               </div>
               <div className = "flex flex-wrap items-center justify-between gap-3">
                  <div className = "relative w-full max-w-xs">
                     <Search className = "absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                     <Input
                        placeholder = "Search domains..."
                        value = {search}
                        onChange = {(e) => set_search(e.target.value)}
                        className = "h-9 pl-9"
                     />
                  </div>
                  <Select value={sort_value} onValueChange = {set_sort_value}>
                     <SelectTrigger className = "w-auto min-w-40">
                        <SelectValue />
                     </SelectTrigger>
                     <SelectContent>
                        {sort_options.map((opt) => (
                           <SelectItem key = {opt.value} value={opt.value}>
                              {opt.value}
                           </SelectItem>
                        ))}
                     </SelectContent>
                  </Select>
               </div>

               {error && (
                  <div className = "rounded-lg border border-brand-alert/30 bg-brand-alert/5 px-4 py-3 text-sm text-brand-alert">
                     {error}
                  </div>
               )}

               <Card className = "border border-brand-panel-border bg-brand-panel ring-0">
                  <CardContent className = "overflow-x-auto px-0 py-0">
                     <table className = "w-full border-collapse text-left">
                        <thread>
                           <tr className = "border-b border-brand-panel-border text-xs whitespace-nowrap text-muted-foreground uppercase tracking-wide">
                              <th className = "px-3 py-2.5 font-medium">Domain</th>
                              <th className = "px-3 py-2.5 font-medium">Status</th>
                              <th className = "px-3 py-2.5 font-medium">
                                 <span className = "inline-flex items-center gap-1">
                                    Added
                                    <ChevronDown className = "size-3"/>
                                 </span>
                              </th>
                              <th className = "px-3 py-2.5 font-medium">Checked</th>
                              <th className = "px-3 py-2.5 font-medium">Action</th>
                           </tr>
                        </thread>
                        <tbody>
                           
                        </tbody>
                     </table>
                  </CardContent>
               </Card>
            </div>
         </div>

      </div>
   )
}
