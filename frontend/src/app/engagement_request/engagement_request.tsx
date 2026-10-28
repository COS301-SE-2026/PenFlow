"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, Boxes, Braces, CalendarDays, Wallet, Check, CheckCircle2, Circle, Cloud, Eye, EyeOff, Globe, MoreHorizontal, Network, Plus, Scan, ShieldCheck, Smartphone, X } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import PageHero from "@/shared/components/PageHero";
import { cn } from "@/lib/utils";
import { validateDomain } from "@/lib/domainValidator";
import { fetch_domains, type domain_item } from "@/lib/domainServices";
import { formatDateRange, formatEnumLabel, formatQuote } from "@/lib/engagementFormat";


type EngagementType  = "black_box" | "grey_box" | "white_box";

type AssetType = "domain" | "ip" | "hostname" | "url";

type AssessmentType = "web_application" | "mobile_application" | "api" | "network" | "cloud" | "other";

interface Asset {
    id:string;
    type :AssetType;
    value :string;
}

interface SubmittedEngagement {
    id: string;
    engagement_type: EngagementType;
    assessment_type: AssessmentType;
    start_date: string | null;
    end_date: string | null;
    asset_count: number;
    estimated_quote: string | number;
}

type FieldKey = "type" | "assessment" | "objective" | "dates" | "contact" | "assets";

const engagementTypeOptions:{
    value: EngagementType;
    label: string;
    shortLabel: string;
    description: string;
    icon : typeof EyeOff;
}[] = [
    {
        value: "black_box",
        label: "Black Box",
        shortLabel: "Black",
        description: "No internal knowledge or access is provided. Testers simulate an external attacker with no prior information.",
        icon : EyeOff,
    },
    {
        value: "grey_box",
        label: "Grey Box",
        shortLabel: "Grey",
        description: "Partial knowledge is shared — e.g. limited credentials or architecture docs — simulating an attacker with some insider access.",
        icon: Eye,

    },

     {
        value: "white_box",
        label: "White Box",
        shortLabel: "White",
        description: "Full knowledge and access, including source code and architecture, for a deep and thorough assessment.",
        icon: Scan,
    },

];

const assessmentTypeOptions: { value: AssessmentType; label: string; icon: typeof Globe; color: string }[] = [
    { value: "web_application", label: "Web Application", icon: Globe, color: "#2bd8f5" },
    { value: "mobile_application", label: "Mobile Application", icon: Smartphone, color: "#a78bfa" },
    { value: "api", label: "API", icon: Braces, color: "#facc15" },
    { value: "network", label: "Network", icon: Network, color: "#4ade80" },
    { value: "cloud", label: "Cloud", icon: Cloud, color: "#60a5fa" },
    { value: "other", label: "Other", icon: MoreHorizontal, color: "#f472b6" },
];

const assetTypeOptions:{value: AssetType; label:string } [] = [
    { value: "domain", label: "Domain" },
    { value: "ip", label: "IP Address" },
    { value: "hostname", label: "Hostname" },
    { value: "url", label: "URL" },


];


const SIMPLE_IP_REGEX = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;

const HOSTNAME_REGEX = /^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$/;

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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


function detectAssetType(value: string): AssetType | null {
    const trimmed = value.trim();
    if (!trimmed) return null;
    if (/^https?:\/\//i.test(trimmed)) return "url";
    if (SIMPLE_IP_REGEX.test(trimmed)) return "ip";
    if (validateDomain(trimmed).valid) return "domain";
    if (HOSTNAME_REGEX.test(trimmed)) return "hostname";
    return null;
}

function autoGrow(element: HTMLTextAreaElement) {
    element.style.height = "auto";
    element.style.height = `${element.scrollHeight + 2}px`;
}


const MIN_ENGAGEMENT_DAYS = 3;


function toIsoDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth()+1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}
function todayIsoDate(): string {
    return toIsoDate(new Date());
}
function addDays(isoDate: string, days: number): string {
    const [year, month, day] = isoDate.split("-").map(Number);
    return toIsoDate(new Date(year, month - 1, day + days));
}
function durationInDays(startDate: string, endDate: string): number | null {
     if (!startDate || !endDate) return null;

    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffMs = end.getTime() - start.getTime();
    return Math.round(diffMs / (1000 * 60 * 60 * 24));
}

function extractErrorMessage(body: unknown): string {
    const fallback = "Failed to submit engagement request.";
    if (!body || typeof body !== "object" || !("detail" in body)) return fallback;
    const detail = (body as { detail: unknown }).detail;

    if (typeof detail === "string") return detail;

    if (Array.isArray(detail)) {
        return detail
            .map((err) => {
                if (err && typeof err === "object" && "msg" in err) {
                    return (err as { msg: string }).msg.replace(/^Value error,\s*/, "");
                }
                return String(err);
            })
            .join(" ")
    }
    return fallback;
}

const STAGES: { title: string; fields: FieldKey[] }[] = [
    { title: "Engagement type", fields: ["type"] },
    { title: "Scoping questionnaire", fields: ["assessment", "objective", "dates", "contact"] },
    { title: "Assets", fields: ["assets"] },
];

const CHECKLIST: { key: FieldKey; label: string }[] = [
    { key: "type", label: "Type" },
    { key: "assessment", label: "Assessment" },
    { key: "objective", label: "Objective" },
    { key: "dates", label: "Dates" },
    { key: "assets", label: "Assets" },
];

const FIELD_ELEMENT_ID: Record<FieldKey, string> = {
    type: "engagement-type",
    assessment: "assessment-type",
    objective: "objective",
    dates: "start-date",
    contact: "primary-contact",
    assets: "asset-value",
};

function stageOf(field: FieldKey): number {
    return STAGES.findIndex((stage) => stage.fields.includes(field));
}

const PANEL = "min-w-0 rounded-[10px] border border-transparent bg-[#0b1625] p-[18px]";
const FIELD_LABEL = "mb-2 block text-[13px] font-semibold text-[#cbd5e1] uppercase";
const FIELD = "h-10 w-full rounded-md border border-brand-panel-border bg-brand-panel-deep px-3 text-sm text-foreground outline-none placeholder:text-muted-foreground focus:border-brand-cyan";
const TEXTAREA = "block w-full resize-none overflow-hidden rounded-md border border-brand-panel-border bg-brand-panel-deep px-3 py-2 text-sm text-foreground outline-none placeholder:text-muted-foreground focus:border-brand-cyan";

function RequiredMark() {
    return <span aria-hidden="true" className="ml-1 text-brand-alert">*</span>;
}

function FieldError({ message }: { message: string | null | false }) {
    if (!message) return null;
    return <p className="m-0 mt-1.5 text-xs text-brand-alert">{message}</p>;
}

function SectionHeader({ number, done, title, description, required = false }: { number: number; done: boolean; title: string; description: string; required?: boolean }) {
    return (
        <div className="mb-4 flex items-start gap-3">
            <span className={cn(
                "grid size-8 shrink-0 place-items-center rounded-lg text-sm font-semibold",
                done ? "bg-brand-success/10 text-brand-success" : "bg-brand-cyan/10 text-brand-cyan"
            )}>
                {done ? <Check className="size-4" /> : number}
            </span>
            <div className="min-w-0">
                <h2 className="m-0 text-lg text-foreground uppercase max-sm:text-base">{title}{required && <RequiredMark />}</h2>
                <p className="m-0 mt-1 text-[15px] text-muted-foreground max-sm:text-sm">{description}</p>
            </div>
        </div>
    );
}


export default function EngagementHome() {
    const[engagementType,setEngagementType] = useState<EngagementType | null>(null);
    const [assessmentType, setAssessmentType] = useState<AssessmentType | undefined>(undefined);
    const [objective ,setObjective] = useState("");
    const [startDate , setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [constraints, setConstraints] = useState("");
    const [primaryContact, setPrimaryContact] = useState("");

    const [assetValue, setAssetValue] = useState("");
    const [assetError, setAssetError] = useState<string | null>(null);
    const [assets, setAssets] = useState<Asset[]>([]);
    const [verifiedDomains, setVerifiedDomains] = useState<domain_item[]>([]);

    const [submitted, setSubmitted] = useState<SubmittedEngagement | null>(null);
    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState<string | null>(null);
    const submitErrorRef = useRef<HTMLDivElement>(null);

    const [touched, setTouched] = useState<Set<FieldKey>>(new Set());
    const [stage, setStage] = useState(0);
    const [focusTarget, setFocusTarget] = useState<FieldKey | null>(null);

    useEffect(() => {
        fetch_domains({ status: "verified", limit: 100 })
            .then((result) => setVerifiedDomains(result.items))
            .catch(() => setVerifiedDomains([]));
    }, []);

    useEffect(() => {
        if (submitted) return;
        document.documentElement.style.setProperty("--ask-penflow-offset", "112px");
        return () => { document.documentElement.style.removeProperty("--ask-penflow-offset"); };
    }, [submitted]);

    useEffect(() => {
        if (submitError) submitErrorRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, [submitError]);

    useEffect(() => {
        if (!focusTarget) return;
        const element = document.getElementById(FIELD_ELEMENT_ID[focusTarget]);
        element?.scrollIntoView({ behavior: "smooth", block: "center" });
        element?.focus({ preventScroll: true });
        setFocusTarget(null);
    }, [focusTarget, stage]);

    function touch(...fields: FieldKey[]) {
        setTouched((prev) => new Set([...prev, ...fields]));
    }

    function addAsset(type: AssetType, value: string) {
        setAssets((prev) => [...prev, { id: crypto.randomUUID(), type, value }]);
        touch("assets");
    }
    function handleAddAsset(){
        const value =assetValue.trim();
        if(!value)return;

        const type = detectAssetType(value);
        if (!type) {
            setAssetError("Enter a domain, IP address, hostname, or a URL starting with http:// or https://.");
            return;
        }
        const error = validateAssetValue(type, value);
        if (error) {
            setAssetError(error);
            return;
        }
        if (assets.some((asset) => asset.value.toLowerCase() === value.toLowerCase())) {
            setAssetError("That asset is already in scope.");
            return;
        }

        addAsset(type, value);
        setAssetValue("");
        setAssetError(null);
    }
    function handleRemoveAsset(id:string){
        setAssets((prev)=>prev.filter((a)=>a.id!==id));
    }
    function handleStartDateChange(value: string) {
        setStartDate(value);
        if (value && (!endDate || (durationInDays(value, endDate) ?? 0) < MIN_ENGAGEMENT_DAYS)) {
            setEndDate(addDays(value, MIN_ENGAGEMENT_DAYS));
        }
    }
    function resetForm() {
        setEngagementType(null);
        setAssessmentType(undefined);
        setObjective("");
        setStartDate("");
        setEndDate("");
        setConstraints("");
        setPrimaryContact("");
        setAssetValue("");
        setAssetError(null);
        setAssets([]);
        setSubmitError(null);
        setTouched(new Set());
        setStage(0);
        setSubmitted(null);
        window.scrollTo({ top: 0 });
    }
    async function handleSubmit(){
        if (!engagementType || submitting) return;

        setSubmitting(true);
        setSubmitError(null);

        try {
            const res = await fetch("/api/engagements", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    engagement_type: engagementType,
                    assessment_type: assessmentType,
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
            setSubmitted(body as SubmittedEngagement);
            window.scrollTo({ top: 0, behavior: "smooth" });
        } catch {
            setSubmitError("Failed to submit engagement request.");
        } finally {
            setSubmitting(false);
        }

    }
    const minDate =  todayIsoDate();
    const startDateValid  = !startDate || startDate >= minDate;
    const durationDays = durationInDays(startDate, endDate);
    const durationValid = durationDays !== null && durationDays >= MIN_ENGAGEMENT_DAYS;

    const errors: Record<FieldKey, string | null> = {
        type: engagementType === null ? "Choose an engagement type." : null,
        assessment: assessmentType === undefined ? "Choose what testers should focus on." : null,
        objective: objective.trim().length === 0 ? "Describe what you want to learn or validate." : null,
        dates: !startDate
            ? "Choose a start date."
            : !startDateValid
                ? "Start date cannot be in the past."
                : !endDate
                    ? "Choose an end date."
                    : !durationValid
                        ? `End date must be at least ${MIN_ENGAGEMENT_DAYS} days after the start date.`
                        : null,
        contact: primaryContact.trim() && !EMAIL_REGEX.test(primaryContact.trim()) ? "Enter a valid email address." : null,
        assets: assets.length === 0 ? "Add at least one asset." : null,
    };
    const showError = (field: FieldKey) => (touched.has(field) ? errors[field] : null);
    const missing = (Object.keys(errors) as FieldKey[]).filter((field) => errors[field]);
    const canSubmit = missing.length === 0;
    const itemsLeft = CHECKLIST.filter((item) => errors[item.key]).length;
    const stageDone = (index: number) => STAGES[index].fields.every((field) => !errors[field]);

    function goToStage(next: number) {
        setStage(next);
        window.scrollTo({ top: 0, behavior: "smooth" });
    }
    function handleNext() {
        const stageFields = STAGES[stage].fields;
        const firstInvalid = stageFields.find((field) => errors[field]);
        if (firstInvalid) {
            touch(...stageFields);
            setFocusTarget(firstInvalid);
            return;
        }
        goToStage(stage + 1);
    }
    function handleSubmitClick() {
        if (!canSubmit) {
            touch(...missing);
            setStage(stageOf(missing[0]));
            setFocusTarget(missing[0]);
            return;
        }
        void handleSubmit();
    }
    function jumpTo(field: FieldKey) {
        if (!errors[field]) return;
        touch(field);
        setStage(stageOf(field));
        setFocusTarget(field);
    }

    const selectedTypeOption = engagementTypeOptions.find((o) => o.value === engagementType);
    const detectedType = detectAssetType(assetValue);
    const suggestedDomains = verifiedDomains.filter((d) => !assets.some((asset) => asset.value.toLowerCase() === d.domain.toLowerCase()));

    if (submitted) {
        return <SubmissionConfirmation engagement={submitted} onSubmitAnother={resetForm} />;
    }
    const stageClassName = (index: number) => cn(stage !== index && "max-sm:hidden");

    return(
        <div className="min-w-0">
            <div className="max-sm:hidden">
                <PageHero title="ENGAGEMENT REQUEST" />
            </div>

        <div className="flex flex-col gap-5 pt-2 max-sm:gap-4 max-sm:pt-2 max-sm:pb-36">
            <div className="hidden flex-col gap-1 max-sm:flex">
              <h1 className="m-0 hidden text-2xl text-foreground max-sm:block">Engagement Request</h1>
               <p className="m-0 hidden text-sm text-muted-foreground max-sm:block">
                Scope a new penetration test in {STAGES.length} stages.
               </p>
            </div>

            <div className="hidden max-sm:block">
                <p className="m-0 mb-2 text-xs text-muted-foreground">
                    Stage {stage + 1} of {STAGES.length} · <strong className="text-brand-cyan">{STAGES[stage].title}</strong>
                </p>
                <div className="flex gap-1">
                    {STAGES.map((s, index) => (
                        <span key={s.title} className={cn("h-1.5 flex-1 rounded-full", index <= stage ? "bg-brand-cyan" : "bg-brand-panel-border")} />
                    ))}
                </div>
            </div>

            {submitError && (
                <Card ref={submitErrorRef} role="alert" className="border-brand-alert/40 bg-brand-alert/10">
                        <CardContent className="py-4">
                            <p className="m-0 text-sm text-foreground">{submitError}</p>
                        </CardContent>
                </Card>
            )}

            <div>
            <div className="flex min-w-0 flex-col gap-5 max-sm:gap-4">

             <section className={cn(PANEL, "max-[650px]:p-3", stageClassName(0))}>
                <SectionHeader number={1} done={stageDone(0)} title="Engagement Type" required description="Select the level of access and knowledge testers should start with." />
                    <div id="engagement-type" tabIndex={-1} role="radiogroup" aria-label="Engagement type" className="outline-none">
                        <div className="hidden grid-cols-3 gap-1 rounded-xl border border-brand-panel-border bg-brand-panel-deep p-1 max-sm:grid">
                            {engagementTypeOptions.map(({ value, shortLabel, icon: Icon }) => {
                                const selected = engagementType === value;
                                return (
                                    <button
                                        key={value}
                                        type="button"
                                        role="radio"
                                        aria-checked={selected}
                                        onClick={() => { setEngagementType(value); touch("type"); }}
                                        className={cn(
                                            "flex min-h-11 items-center justify-center gap-1.5 rounded-lg text-sm font-semibold transition-colors",
                                            selected ? "bg-brand-cyan/15 text-brand-cyan" : "text-muted-foreground"
                                        )}
                                    >
                                        <Icon className="size-4" />
                                        {shortLabel}
                                    </button>
                                );
                            })}
                        </div>
                        <p className="mt-3 hidden text-sm text-muted-foreground max-sm:block">
                            {selectedTypeOption
                                ? <><strong className="text-foreground">{selectedTypeOption.label}:</strong> {selectedTypeOption.description}</>
                                : "Pick how much testers know about your systems before they start."}
                        </p>

                        <div className="grid gap-3.5 sm:grid-cols-3 max-sm:hidden">
                    {engagementTypeOptions.map(({ value, label, description, icon: Icon})=>{
                        const selected = engagementType === value;
                        return(
                            <button
                             key = {value}
                             type = "button"
                             role="radio"
                             aria-checked={selected}
                             onClick={()=> { setEngagementType(value); touch("type"); }}
                             className={cn(
                                "relative flex flex-col items-start gap-2 rounded-[10px] border p-4 text-left transition-colors",
                                selected
                                ? "border-brand-cyan/60 bg-brand-cyan/[0.06]"
                                : "border-brand-panel-border bg-transparent hover:border-brand-cyan/40",
                             )}
                             >
                                <span aria-hidden="true" className={cn(
                                    "absolute top-4 right-4 grid size-[18px] place-items-center rounded-full border-2 transition-colors",
                                    selected ? "border-brand-cyan" : "border-[#334155]"
                                )}>
                                    {selected && <span className="size-2 rounded-full bg-brand-cyan" />}
                                </span>
                                <span className={cn("grid size-9 place-items-center rounded-lg", selected ? "bg-brand-cyan/15 text-brand-cyan" : "bg-white/[0.04] text-muted-foreground")}>
                                    <Icon className="size-5" />
                                </span>
                                <span className="text-base font-semibold text-foreground">{label}</span>
                                <span className="text-[13px] leading-relaxed text-muted-foreground">{description}</span>
                            </button>
                        );
                    })}
                        </div>
                    </div>
                    <FieldError message={showError("type")} />
             </section>

            <section className={cn(PANEL, "max-[650px]:p-3", stageClassName(1))}>
                <SectionHeader number={2} done={stageDone(1)} title="Scoping Questionnaire" description="Tell us about the goals, timeline, and any rules of engagement." />
                    <div className="flex flex-col gap-5 max-sm:gap-4">
                        <div>
                            <span className={FIELD_LABEL}>Assessment type<RequiredMark /></span>
                            <div
                                id="assessment-type"
                                tabIndex={-1}
                                role="radiogroup"
                                aria-label="Assessment type"
                                className="grid grid-cols-6 gap-2 outline-none max-lg:grid-cols-3 max-sm:grid-cols-2"
                            >
                                {assessmentTypeOptions.map(({ value, label, icon: Icon, color }) => {
                                    const selected = assessmentType === value;
                                    return (
                                        <button
                                            key={value}
                                            type="button"
                                            role="radio"
                                            aria-checked={selected}
                                            onClick={() => { setAssessmentType(value); touch("assessment"); }}
                                            className={cn(
                                                "flex min-h-[72px] flex-col items-center justify-center gap-1.5 rounded-md border px-2 py-2.5 text-center text-xs font-medium transition-colors",
                                                selected
                                                    ? "border-brand-cyan/60 bg-brand-cyan/[0.08] text-brand-cyan"
                                                    : "border-brand-panel-border bg-brand-panel-deep text-[#cbd5e1] hover:border-brand-cyan/40"
                                            )}
                                        >
                                            <Icon className="size-5" style={{ color }} />
                                            {label}
                                        </button>
                                    );
                                })}
                            </div>
                             <FieldError message={showError("assessment")} />
                        </div>

                        <div>
                            <label className={FIELD_LABEL} htmlFor="objective">Engagement objective<RequiredMark /></label>
                            <textarea
                                id="objective"
                                value={objective}
                                onChange={(e) => { setObjective(e.target.value); autoGrow(e.currentTarget); }}
                                onBlur={() => touch("objective")}
                                aria-invalid={Boolean(showError("objective"))}
                                placeholder="What are you hoping to learn or validate from this engagement?"
                                rows={2}
                                className={cn(TEXTAREA, showError("objective") && "border-brand-alert")}
                            />
                             <FieldError message={showError("objective")} />
                         </div>

                    <div>
                        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 max-sm:grid-cols-2 max-sm:gap-2.5">
                            <div className="min-w-0">
                                <label className={FIELD_LABEL} htmlFor="start-date">Start date<RequiredMark /></label>
                                <input
                                    id="start-date"
                                    type="date"
                                    min={minDate}
                                    value={startDate}
                                    onChange={(e) => handleStartDateChange(e.target.value)}
                                    onBlur={() => touch("dates")}
                                    aria-invalid={Boolean(showError("dates"))}
                                    className={cn(FIELD, "[color-scheme:dark] max-sm:px-2", showError("dates") && "border-brand-alert")}
                                />
                            </div>
                            <div className="min-w-0">
                                <label className={FIELD_LABEL} htmlFor="end-date">End date<RequiredMark /></label>
                                <input
                                    id="end-date"
                                    type="date"
                                    value={endDate}
                                    min={startDate ? addDays(startDate, MIN_ENGAGEMENT_DAYS) : minDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    onBlur={() => touch("dates")}
                                    aria-invalid={Boolean(showError("dates"))}
                                    className={cn(FIELD, "[color-scheme:dark] max-sm:px-2", showError("dates") && "border-brand-alert")}
                                />
                            </div>
                            <div className="min-w-0 max-lg:sm:col-span-2 max-sm:col-span-2 max-sm:order-last">
                                <label className={FIELD_LABEL} htmlFor="primary-contact">Primary contact email</label>
                                <input
                                    id="primary-contact"
                                    type="email"
                                    inputMode="email"
                                    autoComplete="email"
                                    autoCapitalize="off"
                                    value={primaryContact}
                                    onChange={(e) => setPrimaryContact(e.target.value)}
                                    onBlur={() => touch("contact")}
                                    aria-invalid={Boolean(showError("contact"))}
                                    placeholder="you@company.com"
                                    className={cn(FIELD, showError("contact") && "border-brand-alert")}
                                />
                                <FieldError message={showError("contact")} />
                            </div>
                        </div>
                        {showError("dates") ? (
                            <FieldError message={showError("dates")} />
                        ) : (
                            <p className="m-0 mt-1.5 text-xs text-muted-foreground">
                                Minimum {MIN_ENGAGEMENT_DAYS} days
                                {durationDays !== null && durationDays > 0 && <> · {durationDays} day{durationDays === 1 ? "" : "s"} selected</>}
                            </p>
                        )}
                    </div>

                    <div>
                        <label className={FIELD_LABEL} htmlFor="constraints">Constraints / rules of engagement</label>
                        <textarea
                            id="constraints"
                            value={constraints}
                            onChange={(e) => { setConstraints(e.target.value); autoGrow(e.currentTarget); }}
                            placeholder="Blackout windows, systems to avoid, testing hours etc."
                            rows={2}
                            className={TEXTAREA}
                        />
                    </div>
                    </div>
            </section>

                <section className={cn(PANEL, "max-[650px]:p-3", stageClassName(2))}>
                    <SectionHeader number={3} done={stageDone(2)} title="Asset Declaration" required description="Declare every domain, IP, hostname, or URL that is in scope for this engagement." />
                    <div className="flex flex-col gap-4">
                        {suggestedDomains.length > 0 && (
                            <div>
                                <span className={FIELD_LABEL}>Your verified domains</span>
                                <div className="flex flex-wrap gap-2">
                                    {suggestedDomains.map((d) => (
                                        <button
                                            key={d.id}
                                            type="button"
                                            onClick={() => addAsset("domain", d.domain)}
                                            className="inline-flex items-center gap-1.5 rounded-md border border-brand-panel-border bg-brand-panel-deep px-2.5 py-1.5 text-xs text-[#cbd5e1] transition-colors hover:border-brand-cyan/50 hover:text-brand-cyan"
                                        >
                                            <Plus className="size-3.5" />
                                            <ShieldCheck className="size-3.5 text-brand-success" />
                                            {d.domain}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div>
                            <label className={FIELD_LABEL} htmlFor="asset-value">Add an asset</label>
                            <div className="flex max-w-xl gap-2">
                                <div className="relative min-w-0 flex-1">
                                    <input
                                        id="asset-value"
                                        value={assetValue}
                                        onChange={(e) => { setAssetValue(e.target.value);
                                            setAssetError(null); }}
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter") {
                                                e.preventDefault();
                                                handleAddAsset();
                                            }
                                        }}
                                        inputMode="url"
                                        autoCapitalize="off"
                                        autoCorrect="off"
                                        spellCheck={false}
                                        enterKeyHint="done"
                                        placeholder="example.com, 10.0.0.1 or https://app.example.com"
                                        className={cn(FIELD, detectedType && "pr-28", assetError && "border-brand-alert")}
                                    />
                                    {detectedType && (
                                        <span className="pointer-events-none absolute top-1/2 right-2.5 -translate-y-1/2 rounded-[5px] border border-brand-cyan/40 bg-brand-cyan/10 px-2 py-0.5 text-[9px] font-semibold text-brand-cyan uppercase">
                                            {assetTypeOptions.find((o) => o.value === detectedType)?.label}
                                        </span>
                                    )}
                                </div>
                                <button
                                    type="button"
                                    onClick={handleAddAsset}
                                    className="inline-flex h-10 shrink-0 items-center gap-1.5 rounded-md border border-brand-panel-border bg-brand-panel-deep px-4 text-sm text-[#cbd5e1] transition-colors hover:border-brand-cyan/50 hover:text-brand-cyan"
                                >
                                     <Plus className="size-4" />
                                     <span className="max-sm:hidden">Add asset</span>
                                     <span className="hidden max-sm:inline">Add</span>
                                </button>
                            </div>
                             <p className={cn("m-0 mt-1.5 text-xs", assetError ? "text-brand-alert" : "text-muted-foreground")}>
                                {assetError ?? "Domain, IP address, hostname or URL. The type is detected automatically."}
                            </p>
                        </div>

                        <div className="flex items-center justify-between gap-4 border-t border-brand-panel-border pt-4">
                            <div className="min-w-0">
                                {assets.length === 0 ? (
                        <p className={cn("m-0 text-sm", showError("assets") ? "text-brand-alert" : "text-muted-foreground")}>
                            {showError("assets") ?? "No assets declared yet."}
                        </p>
                    ) : (
                        <div className="flex flex-wrap gap-2">
                            {assets.map((asset) => (
                                <span
                                    key={asset.id}
                                    className="inline-flex max-w-full items-center gap-2 rounded-full border border-brand-panel-border bg-brand-panel-deep py-1 pr-1 pl-3 text-sm"
                                >
                                    <span className="shrink-0 text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
                                        {assetTypeOptions.find((o) => o.value === asset.type)?.label}
                                    </span>
                                    <span className="min-w-0 font-mono break-all text-foreground">{asset.value}</span>
                                    <button
                                        type="button"
                                        onClick={() => handleRemoveAsset(asset.id)}
                                        aria-label={`Remove ${asset.value}`}
                                        className="grid size-7 shrink-0 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-brand-alert/10 hover:text-brand-alert"
                                    >
                                        <X className="size-4" />
                                    </button>
                                </span>
                            ))}
                        </div>
                    )}
                            </div>
                            <Button
                                type="button"
                                disabled={submitting}
                                onClick={handleSubmitClick}
                                className="h-10 shrink-0 px-5 text-sm max-sm:hidden"
                            >
                                {submitting ? "Submitting…" : "Submit Request"}
                            </Button>
                        </div>
                    </div>
                </section>

                 <div className={cn("flex items-center justify-between gap-4 max-sm:flex-col max-sm:items-stretch", stageClassName(STAGES.length - 1))}>
                 <ul className="m-0 flex list-none flex-wrap gap-2 p-0" aria-label="Request checklist">
                    {CHECKLIST.map((item) => {
                        const done = !errors[item.key];
                        return (
                            <li key={item.key}>
                                <button
                                    type="button"
                                    onClick={() => jumpTo(item.key)}
                                    className={cn(
                                        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs",
                                        done
                                            ? "cursor-default border-brand-success/40 bg-brand-success/10 text-brand-success"
                                            : "border-brand-panel-border text-muted-foreground hover:text-foreground"
                                    )}
                                >
                                    {done ? <Check className="size-3.5" /> : <Circle className="size-3.5" />}
                                    {item.label}
                                </button>
                            </li>
                        );
                    })}
                 </ul>
                 </div>
            </div>

            </div>

            <div className="fixed inset-x-0 bottom-0 z-40 hidden border-t border-brand-panel-border bg-[#050914]/95 px-4 pt-2.5 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur max-sm:block">
                <p className={cn("m-0 mb-2 text-xs", canSubmit ? "text-brand-success" : "text-muted-foreground")}>
                    {canSubmit ? "Ready to submit" : `${itemsLeft} item${itemsLeft === 1 ? "" : "s"} left`}
                </p>
                <div className="flex gap-2">
                    {stage > 0 && (
                        <Button type="button" variant="outline" onClick={() => goToStage(stage - 1)} className="h-11 flex-1 text-base">
                            Back
                        </Button>
                    )}
                    {stage < STAGES.length - 1 ? (
                        <Button type="button" onClick={handleNext} className="h-11 flex-[2] text-base">
                            Next
                        </Button>
                    ) : (
                        <Button type="button" disabled={submitting} onClick={handleSubmitClick} className="h-11 flex-[2] text-base">
                            {submitting ? "Submitting…" : "Submit Request"}
                        </Button>
                    )}
                </div>
            </div>
        </div>
        </div>
    )
}

function SubmissionConfirmation({engagement, onSubmitAnother}: {engagement: SubmittedEngagement; onSubmitAnother: () => void}) {
    const typeLabel = engagementTypeOptions.find((o) => o.value === engagement.engagement_type)?.label ?? formatEnumLabel(engagement.engagement_type);
    const assessmentLabel = assessmentTypeOptions.find((o) => o.value === engagement.assessment_type)?.label ?? formatEnumLabel(engagement.assessment_type);
    const days = engagement.start_date && engagement.end_date ? durationInDays(engagement.start_date, engagement.end_date) : null;
    const details: { label: string; value: string; icon: typeof Globe; color: string }[] = [
        { label: "Assessment", value: assessmentLabel, color: "#2bd8f5",
            icon: assessmentTypeOptions.find((o) => o.value === engagement.assessment_type)?.icon ?? Globe },
        { label: "Engagement", value: typeLabel, color: "#a78bfa",
            icon: engagementTypeOptions.find((o) => o.value === engagement.engagement_type)?.icon ?? Eye },
        { label: "Dates", value: `${formatDateRange(engagement.start_date, engagement.end_date)}${days ? ` · ${days} days` : ""}`, icon: CalendarDays, color: "#facc15" },
        { label: "Assets", value: String(engagement.asset_count), icon: Boxes, color: "#f472b6" },
    ];

    return (
        <div className="min-w-0">
            <div className="max-sm:hidden">
                <PageHero title="ENGAGEMENT REQUEST" />
            </div>
        <div className="flex pt-2 max-sm:min-h-[calc(100dvh-8rem)] max-sm:items-center max-sm:py-4">
            <section role="status" aria-live="polite" className={cn(PANEL, "mx-auto w-full max-w-2xl p-7 max-sm:p-4")}>
                <div className="flex flex-col items-center gap-3 text-center">
                    <span className="grid size-14 place-items-center rounded-full bg-brand-success/10 text-brand-success ring-1 ring-brand-success/40 motion-safe:animate-[pop_400ms_ease-out]">
                        <CheckCircle2 className="size-7" />
                    </span>
                    <h1 className="m-0 text-xl text-foreground">Request submitted</h1>
                </div>

                <div className="mt-6 rounded-[10px] border border-brand-panel-border">
                    <dl className="m-0 grid grid-cols-2 gap-x-6 gap-y-5 p-5 max-sm:grid-cols-1 max-sm:p-4">
                        {details.map((item) => (
                            <div key={item.label} className="flex min-w-0 items-center gap-3">
                                <DetailIcon icon={item.icon} color={item.color} />
                                <div className="min-w-0">
                                    <dt className="text-xs font-semibold text-[#94a3b8] uppercase">{item.label}</dt>
                                    <dd className="m-0 mt-0.5 truncate text-base text-foreground">{item.value}</dd>
                                </div>
                            </div>
                        ))}
                    </dl>
                    <div className="flex items-center justify-between gap-4 border-t border-brand-panel-border p-5 max-sm:p-4">
                        <div className="flex min-w-0 items-center gap-3">
                            <DetailIcon icon={Wallet} color="#4ade80" />
                            <div className="min-w-0">
                                <p className="m-0 text-xs font-semibold text-[#cbd5e1] uppercase">Estimated quote</p>
                                <p className="m-0 mt-0.5 text-sm text-muted-foreground">Final quote confirmed after scoping</p>
                            </div>
                        </div>
                        <strong className="shrink-0 text-[32px] leading-none text-foreground">{formatQuote(engagement.estimated_quote)}</strong>
                    </div>
                </div>

                <div className="mt-6">
                    <p className="m-0 mb-1.5 text-xs font-semibold text-[#cbd5e1] uppercase">What happens next</p>
                    <p className="m-0 text-sm text-muted-foreground">
                        Service Delivery will review your request, and you&apos;ll get a notification once it&apos;s scheduled.
                    </p>
                </div>

                <div className="mt-7 flex items-center justify-center gap-3 max-sm:flex-col max-sm:items-stretch">
                    <Button asChild className="h-10 gap-1.5 px-5 text-sm">
                        <Link href={`/pentesting/engagement/${engagement.id}`}>View engagement <ArrowRight className="size-4" /></Link>
                    </Button>
                    <button type="button" onClick={onSubmitAnother} className="h-10 px-3 text-sm text-muted-foreground transition-colors hover:text-brand-cyan">
                        Submit another request
                    </button>
                </div>
            </section>
        </div>
        </div>
    );
}


function DetailIcon({ icon: Icon, color }: { icon: typeof Globe; color: string }) {
    return (
        <span
            className="grid size-10 shrink-0 place-items-center rounded-lg"
            style={{ color, backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)` }}
        >
            <Icon className="size-5" />
        </span>
    );
}