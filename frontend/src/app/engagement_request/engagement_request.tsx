//engagement home screen
"use client";

import { useState } from "react";
import { Eye, EyeOff, Scan, Plus, Trash2, CheckCircle2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/shared/components/ui/button";
import { Separator } from "@/shared/components/ui/separator";
import { cn } from "@/lib/utils";
import { validateDomain } from "@/lib/domainValidator";


//type declaration 
type EngagementType  = "black_box" | "grey_box" | "white_box";

type AssetType = "domain" | "ip" | "hostname" | "url";

interface Asset {
    id:string;
    type :AssetType;
    value :string;
}

const engagementTypeOptions:{
    value: EngagementType;
    label: string;
    description: string;
    icon : typeof EyeOff;
}[] = [
    {
        value: "black_box",
        label: "Black Box",
        description: "No internal knowledge or access is provided.Testers simulate an external attacker with no prior information.",
        icon : EyeOff,
    },
    {
        value: "grey_box",
        label: "Grey Box",
        description: "Partial knowledge is shared — e.g. limited credentials or architecture docs — simulating an attacker with some insider access.",
        icon: Eye,

    },

     {
        value: "white_box",
        label: "White Box",
        description: "Full knowledge and access, including source code and architecture, for a deep and thorough assessment.",
        icon: Scan,
    },

];

const assetTypeOptions:{value: AssetType; label:string } [] = [
    { value: "domain", label: "Domain" },
    { value: "ip", label: "IP Address" },
    { value: "hostname", label: "Hostname" },
    { value: "url", label: "URL" },


];

//hint for each asset type
const assetTypeHints: Record<AssetType, string> = {
    domain: "e.g. example.com",
    ip: "e.g. 10.0.0.1",
    hostname:"e.g. server.local",
    url: "must start with http:// or https://, e.g. https://example.com",
}

//simple ip check for ip for 1-3 numbers
const SIMPLE_IP_REGEX = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;

//sane rules for backend validate
const HOSTNAME_REGEX = /^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$/;

//validate asset function
function validateAssetValue(type: AssetType, value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) return "Value is required.";
    switch (type) {
        case "domain": {
            const result = validateDomain(trimmed);
            return result.valid ? null : result.error;
        }
        case "ip":
            return SIMPLE_IP_REGEX.test(trimmed)
                ? null
                : "Asset value must be a valid IP address (e.g. 10.0.0.1).";
        case "hostname":
            return HOSTNAME_REGEX.test(trimmed)
                ? null
                : "Asset value must be a valid hostname (letters, digits, hyphens, and dots only).";
        case "url":
            return trimmed.startsWith("http://") || trimmed.startsWith("https://")
                ? null
                : "URL assets must start with http:// or https://.";
    }
}


//control to have min 7 days for a request
const MIN_ENGAGEMENT_DAYS = 7;
function durationInDays(startDate: string, endDate: string): number | null {
     if (!startDate || !endDate) return null;

    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffMs = end.getTime() - start.getTime();
    return Math.round(diffMs / (1000 * 60 * 60 * 24));
}

// extract error message and convert to UI user can see
function extractErrorMessage(body: unknown): string {
    const fallback = "Failed to submit engagement request.";
    if (!body || typeof body !== "object" || !("detail" in body)) return fallback;
    const detail = (body as { detail: unknown }).detail;

    if (typeof detail === "string") return detail;

    if (Array.isArray(detail)) {
        return detail
            .map((err) => {
                if (err && typeof err === "object" && "msg" in err) {
                   
                    //remove pydantic defualt message value error
                    return (err as { msg: string }).msg.replace(/^Value error,\s*/, "");
                }
                return String(err);
            })
            .join(" ")
    }
    return fallback;
}


export default function EngagementHome() {
    const[engagementType,setEngagementType] = useState<EngagementType | null>(null);
   
    const [objective ,setObjective] = useState("");
    const [startDate , setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [constraints, setConstraints] = useState("");
    const [primaryContact, setPrimaryContact] = useState("");

    const [assetType, setAssetType] = useState<AssetType>("domain");
    const [assetValue, setAssetValue] = useState("");
    const [assetError, setAssetError] = useState<string | null>(null);
    const [assets, setAssets] = useState<Asset[]>([]);

    const [submitted, setSubmitted] = useState(false) ;
    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState<string | null>(null);
    const [estimatedQuote, setEstimatedQuote] = useState<string | null>(null);


    function handleAddAsset(){
        const value =assetValue.trim();
        if(!value)return;

        const error = validateAssetValue(assetType, value);
        if (error) {
            setAssetError(error);
            return;
        }

        setAssets((prev) => [...prev, { id: crypto.randomUUID(), type: assetType, value}]);
        setAssetValue("");
        setAssetError(null);
    }
    function handleRemoveAsset(id:string){
        setAssets((prev)=>prev.filter((a)=>a.id!==id));
    }
    async function handleSubmit(){   
        if (!engagementType) return;

        setSubmitting(true);
        setSubmitError(null);
        setSubmitted(false);
        setEstimatedQuote(null);
        
        try {
            const res = await fetch("/api/engagements", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    engagement_type: engagementType,
                    objective,
                    start_date: startDate || null,
                    end_date: endDate || null,
                    constraints: constraints || null,
                    primary_contact: primaryContact || null,
                    assets: assets.map(({ type, value }) => ({ type, value })),
                }),
            });
            const body = await res.json().catch(() => null);
            if (!res.ok) {
                setSubmitError(extractErrorMessage(body));
                return;
            }
            setEstimatedQuote(body.estimated_quote);
            setSubmitted(true);
        } catch {
            setSubmitError("Failed to submit engagement request.");
        } finally {
            setSubmitting(false);
        }
        
    }
    const durationDays = durationInDays(startDate, endDate);
    const durationValid = durationDays !== null && durationDays >= MIN_ENGAGEMENT_DAYS;
    const canSubmit = engagementType !== null && objective.trim().length > 0 && assets.length > 0 && durationValid;

    return(
        <div className="mx-auto flex max-w-4xl flex-col gap-8 px-4 py-10 text-lg">
            <div className="flex flex-col gap-2">
              <h1 className="text-4xl font-bold text-foreground">Engagement Request</h1>
               <p className="text-lg text-muted-foreground">
                Scope out a new penetration testing engagement — choose an engagement type, fill in the
                scoping questionnaire, and declare the assets that are in scope.
               </p>
            </div>

            {submitted && (
            <Card className = "border-brand-success/40 bg-brand-success/10">
                <CardContent className="flex items-center gap-3 py-4">
                    <CheckCircle2 className="size-6 shrink-0 text-brand-success" />
                    <p className="text-lg text-foreground">
                        Engagement request captured. 
                            {estimatedQuote !== null && (
                                <> Estimated quote : <span className="font-semibold">R{estimatedQuote}</span>.
                                </>
                            )}
                    </p>
                </CardContent>
            </Card>
            
            )}
            {submitError && (
                <Card className="border-brand-alert/40 bg-brand-alert/10">
                        <CardContent className="py-4">
                            <p className="text-lg text-foreground">{submitError}</p>
                        </CardContent>
                </Card>
            )}
             {/* Engagement type selection */}
             <Card>
                <CardHeader>
                    <CardTitle className="text-2xl">Engagement Type</CardTitle>
                    <CardDescription className="text-base">
                        Select the level of access and knowledge testers should start with.
                    </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-3">
                    {engagementTypeOptions.map(({ value, label, description, icon: Icon})=>{
                        const selected = engagementType === value;
                        return(
                            <button
                             key = {value}
                             type = "button"
                             onClick={()=> setEngagementType(value)}
                             className={cn(
                                "flex flex-col items-start gap-3 rounded-xl border p-4 text-left transition-colors",
                                selected
                                ? "border-brand-cyan bg-brand-cyan/10"
                                : "border-brand-panel-border bg-brand-panel-deep hover:border-brand-cyan/50",
                             )}
                             >
                             <Icon className={cn("size-6", selected ?"text-brand-cyan":"text-muted-foreground")} />
                                <span className="text-xl font-semibold text-foreground">{label}</span>
                                <span className="text-base text-muted-foreground">{description}</span>
                            </button>
                        );
                    })}

                </CardContent>
             </Card>
            {/* Scoping questionnaire */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-2xl">Scoping Questionnaire</CardTitle>
                    <CardDescription className="text-base">
                        Tell us about the goals, timeline, and any rules of engagement.
                    </CardDescription>
                </CardHeader>
                    <CardContent className="flex flex-col gap-5">
                        <div className="flex flex-col gap-2">
                            <Label className="text-base" htmlFor="objective">Engagement objective</Label>
                             <textarea
                            id="objective"
                            value={objective}
                            onChange={(e) => setObjective(e.target.value)}
                             placeholder="What are you hoping to learn or validate from this engagement?"
                            rows={3}
                            className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-lg outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                        />
                         </div>

                          <div className="grid gap-5 sm:grid-cols-2">
                        <div className="flex flex-col gap-2">
                            <Label className="text-base" htmlFor="start-date">Start date</Label>
                            <Input
                                id="start-date"
                                type="date"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                className="h-11 text-xl text-foreground [color-scheme:dark]"
                            />
                        </div>
                        <div className="flex flex-col gap-2">
                            <Label className="text-base" htmlFor="end-date">End date</Label>
                            <Input
                                id="end-date"
                                type="date"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                className="h-11 text-xl text-foreground [color-scheme:dark]"
                            />
                        </div>
                    </div>
                    {startDate && endDate && !durationValid && (
                         <p className="text-base text-brand-alert">
                            Engagements must run for at least {MIN_ENGAGEMENT_DAYS} days. Selected duration: {durationDays} day{durationDays === 1 ? "" : "s"}.
                         </p>

                    )}


                    <div className="flex flex-col gap-2">
                        <Label className="text-base" htmlFor="constraints">Constraints / rules of engagement</Label>
                        <textarea
                            id="constraints"
                            value={constraints}
                            onChange={(e) => setConstraints(e.target.value)}
                            placeholder="Blackout windows, systems to avoid, testing hours etc."
                            rows={3}
                            className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-lg outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                        />
                    </div>


                    <div className="flex flex-col gap-2">
                        <Label className="text-base" htmlFor="primary-contact">Primary contact</Label>
                        <Input
                            id="primary-contact"
                            value={primaryContact}
                            onChange={(e) => setPrimaryContact(e.target.value)}
                            placeholder="name"
                            className="h-11 text-lg"
                        />
                    </div>
                    </CardContent>
            </Card> 
            {/* Asset declaration */}
                <Card>
                    <CardHeader>
                            <CardTitle className="text-2xl">Asset Declaration</CardTitle>
                             <CardDescription className="text-base">
                                Declare every domain, IP, hostname, or URL that is in scope for this engagement.
                             </CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-4">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                            <div className="flex flex-col gap-2 sm:w-48">
                            <Label className="text-base">Asset type</Label>
                             <Select value={assetType} onValueChange={(v) => { setAssetType(v as AssetType); 
                                setAssetError(null); }}>
                             <SelectTrigger className="h-11 text-lg">
                                 <SelectValue/>
                             </SelectTrigger>
                             <SelectContent>
                                {assetTypeOptions.map((opt) => (
                                    <SelectItem key={opt.value} value={opt.value}>
                                        {opt.label}
                                    </SelectItem>
                                ))}
                             </SelectContent>
                         </Select>
                                <p className="text-sm text-muted-foreground invisible">spacer</p>
                        </div>

                        <div className="flex flex-1 flex-col gap-2">
                            <Label className="text-base">Value</Label>
                            <Input
                                value={assetValue}
                                onChange={(e) => { setAssetValue(e.target.value); 
                                    setAssetError(null); }}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter") {
                                        e.preventDefault();
                                        handleAddAsset();
                                    }
                                }}
                                placeholder="Enter value"
                                className={cn("h-11 text-lg", assetError && "border-brand-alert")}
                            />
                             <p className={cn("text-sm", assetError ? "text-brand-alert" : "text-muted-foreground")}>
                                {assetError ?? assetTypeHints[assetType]}
                            </p>
                             </div>
                            <Button type="button" size="lg" onClick={handleAddAsset} className="h-11 gap-2 text-base">
                                 <Plus className="size-4" />
                                 Add asset
                            </Button>
                             </div>


                             <Separator />
                                {assets.length === 0 ? (
                        <p className="text-base text-muted-foreground">No assets declared yet.</p>
                    ) : (
                        <div className="flex flex-col gap-2">
                            {assets.map((asset) => (
                                <div
                                    key={asset.id}
                                    className="flex items-center justify-between rounded-lg border border-brand-panel-border bg-brand-panel-deep px-4 py-3"
                                >
                                    <div className="flex items-center gap-3">
                                        <Badge variant="outline" className="text-sm uppercase tracking-wide">
                                            {assetTypeOptions.find((o) => o.value === asset.type)?.label}
                                        </Badge>
                                        <span className="font-mono text-lg text-foreground">{asset.value}</span>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => handleRemoveAsset(asset.id)}
                                        aria-label={`Remove ${asset.value}`}
                                        className="text-muted-foreground transition-colors hover:text-brand-alert"
                                    >
                                        <Trash2 className="size-5" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}   
                    </CardContent>
                </Card>

                 {/* Review & submit */}
                 <div className="flex items-center justify-between gap-4">
                 <p className="text-base text-muted-foreground">
                    {canSubmit
                        ?"Ready to submit."
                         :`Select an engagement type, fill in the objective, declare at least one asset, and choose a start/end date at least ${MIN_ENGAGEMENT_DAYS} days apart.`
                    }
                 </p>
                 <Button
                 type = "button"
                 size = "lg"
                 disabled ={!canSubmit || submitting}
                 onClick={handleSubmit}
                 className="h-12 px-6 text-lg"
                 >
                    {submitting ? "Submitting…" : "Submit Request"}
                 </Button>
                 </div>
        </div>
    )
}