"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CalendarClock, CheckCircle2, Clock3, Edit3, Pause, Play, Plus, Radar, RefreshCw, Trash2, X} from "lucide-react";

import { fetch_domains, type domain_item } from "@/lib/domainServices";

import { 
    createScanSchedule, 
    deleteScanSchedule, 
    listScanSchedules, 
    updateScanSchedule, 
    type CreateScanSchedule,
    type ScanSchedule,
    type ScanScheduleFrequency,
} from "@/lib/scanScheduleService";
import DashboardLayout from "@/shared/components/DashboardLayout";
import PageHero from "@/shared/components/PageHero";

const WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
];

const TIMEZONES = [
    "Africa/Johannesburg",
    "UTC",
    "Europe/London",
    "America/New_York",
];

const headingClass = "m-0 text-[1.05rem] tracking-[0.045em] text-[var(--col-text)]";

const descriptionClass = "mt-[0.35rem] mb-0 max-w-[680px] text-[0.82rem] leading-[1.5] text-[var(--col-muted)]";

const buttonBaseClass = "inline-flex cursor-pointer items-center justify-center gap-[0.4rem] rounded-[0.55rem] text-[0.8rem] " +
" font-[650] transition-[border-color,background-color,color,transform,box-shadow] duration-[160ms] disabled:cursor-not-allowed disabled:opacity-55";

const primaryButtonClass = `${buttonBaseClass} min-h-[2.35rem] border border-[var(--col-cyan)] bg-[var(--col-cyan)] px-[0.9rem] py-[0.55rem]
 text-[var(--col-navy)] enabled:hover:-translate-y-px enabled:hover:shadow-[0_0_20px_rgba(43,216,245,0.32)]`;

const secondaryButtonClass = `${buttonBaseClass} min-h-[2.15rem] border border-[var(--col-panel-border)] bg-[var(--col-panel-deep)] px-[0.75rem] py-[0.45rem]
 text-[var(--col-text)] enabled:hover:border-[var(--col-edge-hot)] enabled:hover:bg-[rgba(43,216,245,0.06)] enabled:hover:text-[var(--col-cyan)]`;

const dangerButtonClass = `${buttonBaseClass} min-h-[2.15rem] w-[2.15rem] border border-[rgba(255,95,78,0.28)] bg-[rgba(255,95,78,0.06)] text-[var(--col-alert)]
 enabled:hover:border-[var(--col-alert)] enabled:hover:bg-[rgba(255,95,78,0.12)] max-[700px]:w-full`;

const iconButtonClass = `${buttonBaseClass} h-8 w-8 border border-transparent bg-transparent text-[var(--col-muted)] enabled:hover:bg-white/4
 enabled:hover:text-[var(--col-text)]`;

const fieldClass = "flex min-w-0 flex-col gap-[0.4rem]";

const fieldLabelClass = "text-[0.76rem] font-[650] text-[var(--col-text)]";

const fieldControlClass = "min-h-[2.4rem] w-full rounded-[0.5rem] border border-[var(--col-panel-border)] bg-[var(--col-panel-deep)] px-[0.65rem] " +
"py-2 text-[0.82rem] text-[var(--col-text)] outline-none focus:border-[var(--col-cyan)] focus:shadow-[0_0_0_3px_rgba(43,216,245,0.1)] " +
"disabled:cursor-not-allowed disabled:opacity-65";

const fieldHelpClass = "text-[0.7rem] leading-[1.4] text-[var(--col-muted)]";

const errorMessageClass = "rounded-[0.6rem] border border-[rgba(255,95,78,0.3)] bg-[rgba(255,95,78,0.06)] px-[0.9rem] py-3 " +
"text-[0.8rem] text-[var(--col-alert)]";

 

interface ScheduleFormState {
    verified_domain_id: string;
    frequency: ScanScheduleFrequency;
    run_time: string;
    day_of_week: number;
    day_of_month: number;
    timezone: string;
}

const EMPTY_FORM: ScheduleFormState = {
    verified_domain_id: "",
    frequency: "weekly",
    run_time: "09:00",
    day_of_week: 0,
    day_of_month: 1,
    timezone: "Africa/Johannesburg",
};

function formatDateTime(value: string | null): string {
    if(!value) {
        return "Never";
    }

    const date = new Date(value);

    if(Number.isNaN(date.getTime())) {
        return "Unavailable";
    }

    return date.toLocaleString("en-ZA", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function formatRunTime(value: string): string {
    return value.slice(0, 5);
}

function recurrenceDescription(schedule: ScanSchedule): string {
    const time = formatRunTime(schedule.run_time);

    if(schedule.frequency === "weekly" && schedule.day_of_week !== null) {
        return `Every ${WEEKDAYS[schedule.day_of_week]} at ${time}`;
    }

    if(schedule.frequency === "monthly" && schedule.day_of_month !== null) {
        return `Day ${schedule.day_of_month} of every month at ${time}`;
    }

    return "Invalid recurrence configuration";
}

function scheduleToForm(schedule: ScanSchedule): ScheduleFormState {
    return {
        verified_domain_id: schedule.verified_domain_id,
        frequency: schedule.frequency,
        run_time: formatRunTime(schedule.run_time),
        day_of_week: schedule.day_of_week ?? 0,
        day_of_month: schedule.day_of_month ?? 1,
        timezone: schedule.timezone,
    };
}

export default function ScheduledScansPage() {
    const [schedules, setSchedules] = useState<ScanSchedule[]>([]);
    const [domains, setDomains] = useState<domain_item[]>([]);
    const [loading, setLoading] = useState(true);
    const [workingId, setWorkingId] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);
    const [pageError, setPageError] = useState<string | null>(null);
    const [formError, setFormError] = useState<string | null>(null);
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [form, setForm] = useState<ScheduleFormState>(EMPTY_FORM);


    const domainNames = useMemo(
        () => new Map(
            domains.map((domain) => [
                domain.id,
                domain.domain,
            ]
        ),
    ),
    [domains],
);

    const activeCount = schedules.filter(
        (schedule) => schedule.is_active,
    ).length;

    const pausedCount = schedules.length - activeCount;

    const loadData = useCallback(async() => {
        setLoading(true)
        setPageError(null)
        try {
            const [scheduleResult, domainResult] = await Promise.all([
                listScanSchedules(),
                fetch_domains({
                    status: "verified",
                    sort: "domain",
                    order: "asc",
                    limit: 100,
                    offset: 0,
                }),
            ]);

            setSchedules(scheduleResult);
            setDomains(domainResult.items);
        } catch (error) {
            setPageError(
                error instanceof Error
                ? error.message : "Failed to load scheduled scans",
            );
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadData();
    }, [loadData]);

    function openCreateForm() {
        setEditingId(null);
        setFormError(null);
        setForm({
            ...EMPTY_FORM,
            verified_domain_id: domains[0]?.id ?? "",
        });
        setShowForm(true);
    }

    function openEditForm(schedule: ScanSchedule) {
        setEditingId(schedule.id);
        setFormError(null);
        setForm(scheduleToForm(schedule));
        setShowForm(true);
    }

    function closeForm() {
        setShowForm(false);
        setEditingId(null);
        setFormError(null);
    }

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();

        if(!form.verified_domain_id) {
            setFormError("Select a verified domain.");
            return;
        }
        setSubmitting(true);
        setFormError(null);

        const recurrence = {
            frequency: form.frequency,
            run_time: form.run_time,
            day_of_week: form.frequency === "weekly"
            ? form.day_of_week: null,
            day_of_month: form.frequency === "monthly"
            ? form.day_of_month: null,
            timezone: form.timezone,
        };

        try {
            if(editingId) {
                await updateScanSchedule(
                    editingId,
                    recurrence,
                );
            } else {
                const payload: CreateScanSchedule = {
                    verified_domain_id: form.verified_domain_id,
                    scan_type: "active_vulnerability",
                    ...recurrence,
                };

                await createScanSchedule(payload);
            }
            closeForm();
            await loadData();
        } catch(error) {
            setFormError(
                error instanceof Error
                ? error.message : "Failed to save the scan schedule",
            );
        } finally {
            setSubmitting(false);
        }
    }

    async function toggleSchedule(schedule: ScanSchedule) {
        setWorkingId(schedule.id);
        setPageError(null);

        try {
            await updateScanSchedule(schedule.id, {
                is_active: !schedule.is_active,
            });

            await loadData();
        } catch(error) {
            setPageError(
                error instanceof Error
                ? error.message : "Failed to update the schedule",
            );
        } finally {
            setWorkingId(null);
        }
    }

    async function removeSchedule(schedule: ScanSchedule) {
        const domainName = domainNames.get(
            schedule.verified_domain_id,
        ) ?? "this domain";

        const confirmed = window.confirm(
            `Delete the recurring scan for ${domainName}?`,
        );

        if(!confirmed) {
            return;
        }

        setWorkingId(schedule.id);
        setPageError(null);

        try {
            await deleteScanSchedule(schedule.id);

            if(editingId === schedule.id) {
                closeForm();
            }

            await loadData();
        } catch(error) {
            setPageError(
                error instanceof Error
                ? error.message : "Failed to delete the schedule",
            );
        } finally {
            setWorkingId(null);
        }
    }

    return (
        <DashboardLayout>
            <div className="flex min-w-0 flex-col gap-6">
                <PageHero title="SCHEDULED SCANS" />
                <section className = "flex flex-col gap-5">
                    <div className= "flex items-start justify-between gap-4 max-[700px]:flex-col max-[700px]:items-stretch">
                        <div>
                            <h2 className={headingClass}>Recurring active scans</h2>
                            <p className={descriptionClass}>
                                Run verified-domain scans weekly or monthly and compare each result
                                with the previous scheduled scan.
                            </p>
                        </div>

                        <button type="button" className={`${primaryButtonClass} max-[700px]:w-full`} onClick={openCreateForm}
                            disabled={domains.length===0}>
                                <Plus size={16} />
                                New schedule
                        </button>
                    </div>

                    <div className={"grid grid-cols-3 gap-[0.8rem] max-[700px]:grid-cols-1"}>
                        <article className={
                            "flex min-w-0 items-center gap-[0.8rem] rounded-[0.75rem] border border-[var(--col-panel-border)] " +
                            "bg-[linear-gradient(145deg,var(--col-panel),var(--col-panel-deep))] p-4 shadow-[var(--sh-sm)]"}
                        >
                            <span className={
                                "inline-flex h-[2.35rem] w-[2.35rem] flex-none items-center justify-center rounded-[0.55rem] border border-[rgba(43,216,245,0.24)] " +
                                "bg-[rgba(43,216,245,0.08)] text-[var(--col-cyan)]"}
                            >
                                <CalendarClock size={18} />
                            </span>
                            <div className="flex min-w-0 flex-col">
                                <strong className="text-xl text-[var(--col-text)]">{schedules.length}</strong>
                                <span className="text-[0.76rem] text-[var(--col-muted)]">Total schedules</span>
                            </div>
                        </article>

                        <article className={
                            "flex min-w-0 items-center gap-[0.8rem] rounded-[0.75rem] border border-[var(--col-panel-border)] " +
                            "bg-[linear-gradient(145deg,var(--col-panel),var(--col-panel-deep))] p-4 shadow-[var(--sh-sm)]"}
                        >
                            <span className={
                                "inline-flex h-[2.35rem] w-[2.35rem] flex-none items-center justify-center rounded-[0.55rem] border border-[rgba(43,216,245,0.24)] " +
                                "bg-[rgba(43,216,245,0.08)] text-[var(--col-cyan)]"}
                            >
                                <CheckCircle2 size={18} />
                            </span>
                            <div className="flex min-w-0 flex-col">
                                <strong className="text-xl text-[var(--col-text)]">{activeCount}</strong>
                                <span className="text-[0.76rem] text-[var(--col-muted)]">Active</span>
                            </div>
                        </article>

                        <article className={
                            "flex min-w-0 items-center gap-[0.8rem] rounded-[0.75rem] border border-[var(--col-panel-border)] " +
                            "bg-[linear-gradient(145deg,var(--col-panel),var(--col-panel-deep))] p-4 shadow-[var(--sh-sm)]"}
                        >
                            <span className={
                                "inline-flex h-[2.35rem] w-[2.35rem] flex-none items-center justify-center rounded-[0.55rem] border border-[rgba(43,216,245,0.24)] " +
                                "bg-[rgba(43,216,245,0.08)] text-[var(--col-cyan)]"}
                            >
                                <Pause size={18} />
                            </span>
                            <div className="flex min-w-0 flex-col">
                                <strong className="text-xl text-[var(--col-text)]">{pausedCount}</strong>
                                <span className="text-[0.76rem] text-[var(--col-muted)]">Paused</span>
                            </div>
                        </article>
                    </div>

                    {domains.length === 0 && !loading && (
                        <div className={"flex gap-[0.8rem] rounded-[0.75rem] border border-[rgba(245,200,66,0.28)] " +
                            "bg-[rgba(245,200,66,0.06)] p-4 text-[var(--col-yellow)]"}
                        >
                            <Radar size={18} className="mt-[0.15rem] flex-none" />
                            <div>
                                <strong className="text-[0.88rem] text-[var(--col-text)]">No verified domains are available.</strong>
                                <p className="mt-1 mb-[0.45rem] text-[0.8rem] text-[var(--col-muted)]">Verify a domain before creating an active scan schedule.</p>
                                <Link href="/domains" className="text-[0.8rem] font-[650] text-[var(--col-cyan)]">Go to domains</Link>
                            </div>
                        </div>
                    )}

                    {pageError && (
                        <div className={errorMessageClass}>
                            {pageError}
                        </div>
                    )}

                    {showForm && (
                        <form className={
                            "flex flex-col gap-[1.1rem] rounded-[0.8rem] border border-[rgba(43,216,245,0.3)] " +
                            "bg-[linear-gradient(145deg,var(--col-panel),var(--col-panel-deep))] p-[1.1rem] shadow-[var(--sh-glow-cyan)]"}
                            onSubmit={(event) => void handleSubmit(event)}
                        >
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <h2 className={headingClass}>
                                        {editingId ? "Edit schedule": "Create schedule"}
                                    </h2>
                                    <p className={descriptionClass}>Times are interpreted using the selected timezone.</p>
                                </div>

                                <button type="button" className={iconButtonClass} onClick={closeForm}
                                    aria-label="Close schedule form">
                                        <X size={18} />
                                </button>
                            </div>

                            <div className="grid grid-cols-2 gap-[0.9rem] max-[700px]:grid-cols-1">
                                <label className={fieldClass}>
                                    <span className={fieldLabelClass}>Verified domain</span>
                                    <select className={fieldControlClass} 
                                        value={form.verified_domain_id}
                                        disabled={editingId !== null || submitting}
                                        onChange={(event) => {
                                            setForm((current) => ({
                                                ...current,
                                                verified_domain_id: event.target.value,
                                            }));
                                        }}
                                    >
                                        <option value="">
                                            Select a domain
                                        </option>

                                        {domains.map((domain) => (
                                            <option key={domain.id} value={domain.id}>
                                                {domain.domain}
                                            </option>
                                        ))}
                                    </select>

                                    {editingId && (
                                        <small className={fieldHelpClass}>Create a new schedule to change the target.</small>
                                    )}
                                </label>

                                <label className={fieldClass}>
                                    <span className={fieldLabelClass}>Frequency</span>
                                    <select className={fieldControlClass} value={form.frequency} disabled={submitting} onChange={(event) => {
                                        setForm((current) => ({
                                            ...current,
                                            frequency: event.target.value as ScanScheduleFrequency,
                                        }));
                                    }}
                                    >
                                        <option value="weekly">Weekly</option>
                                        <option value="monthly">Monthly</option>
                                    </select>
                                </label>

                                {form.frequency === "weekly" ? (
                                    <label className={fieldClass}>
                                        <span className={fieldLabelClass}>Day of week</span>
                                        <select className={fieldControlClass} 
                                            value={form.day_of_week} 
                                            disabled={submitting} 
                                            onChange={(event) => {
                                            setForm((current) => ({
                                                ...current,
                                                day_of_week: Number(event.target.value),
                                            }));
                                        }}
                                        >
                                            {WEEKDAYS.map((weekday, index) => (
                                                <option key={weekday} value={index}>
                                                    {weekday}
                                                </option>
                                            ))}
                                        </select>
                                    </label>
                                ) : (
                                    <label className={fieldClass}>
                                        <span className={fieldLabelClass}>Day of month</span>
                                        <input className={fieldControlClass} 
                                            type="number" min={1} max={28} value={form.day_of_month}
                                            disabled={submitting} onChange={(event) => {
                                                setForm((current) => ({
                                                    ...current,
                                                    day_of_month: Number(event.target.value)
                                                }));
                                            }}
                                            />
                                            <small className={fieldHelpClass}>
                                                Limited to 1-28 for predictable monthly runs.
                                            </small>
                                    </label>
                                )}

                                <label className={fieldClass}>
                                    <span className={fieldLabelClass}>Run time</span>
                                    <input className={fieldControlClass} 
                                        type="time" value={form.run_time} step={60} disabled={submitting}
                                        onChange={(event) => {
                                            setForm((current) => ({
                                                ...current,
                                                run_time: event.target.value,
                                            }));
                                        }}
                                    />
                                </label>

                                <label className={fieldClass}>
                                    <span className={fieldLabelClass}>Timezone</span>
                                    <select className={fieldControlClass} 
                                        value={form.timezone} disabled={submitting} onChange={(event) => {
                                        setForm((current) => ({
                                            ...current,
                                            timezone: event.target.value,
                                        }));
                                    }}
                                    >
                                        {TIMEZONES.map((timezone) => (
                                            <option key={timezone} value={timezone}>{timezone}</option>
                                        ))}
                                    </select>
                                </label>
                            </div>

                            {formError && (
                                <div className={errorMessageClass}>
                                    {formError}
                                </div>
                            )}

                            <div className="flex justify-end gap-[0.6rem] pt-[0.2rem]">
                                <button type="button" className={secondaryButtonClass} onClick={closeForm} disabled={submitting}>
                                    Cancel
                                </button>

                                <button type="submit" className={primaryButtonClass} disabled={
                                    submitting || !form.verified_domain_id || !form.run_time
                                }
                                >
                                    {submitting ? "Saving...": editingId ? "Save changes": "Create schedule"}
                                </button>
                            </div>
                        </form>
                    )}

                    <div className="flex items-start justify-between gap-4 max-[700px]:flex-col max-[700px]:items-stretch">
                        <div>
                            <h2 className={headingClass}>Your schedules</h2>
                            <p className={descriptionClass}>
                                Paused schedules retain their configuration but will not create scans.
                            </p>
                        </div>

                        <button type="button" className={`${secondaryButtonClass} max-[700px]:w-full`} onClick={() => void loadData()} disabled={loading}>
                            <RefreshCw size={15} className={loading ? "animate-spin" : undefined} />
                            Refresh
                        </button>
                    </div>

                    {loading && schedules.length === 0 ? (
                        <div className={"flex min-h-[220px] flex-col items-center justify-center rounded-[0.8rem] border border-dashed border-[var(--col-panel-border)] " +
                            "bg-[rgba(16,24,39,0.55)] p-8 text-center text-[var(--col-muted)]"}
                        >
                            <Clock3 size={28} className="mb-[0.6rem] text-[var(--col-cyan)]" />
                            <h3 className="m-0 text-[0.95rem] text-[var(--col-text)]">Loading schedules</h3>
                            <p className="mt-[0.4rem] mb-0 text-[0.78rem]">Retrieving your recurring scan configuration.</p>
                        </div>
                    ) : schedules.length === 0 ? (
                        <div className={"flex min-h-[220px] flex-col items-center justify-center rounded-[0.8rem] border border-dashed border-[var(--col-panel-border)] " +
                            "bg-[rgba(16,24,39,0.55)] p-8 text-center text-[var(--col-muted)]"}
                        >
                            <CalendarClock size={30} className="mb-[0.6rem] text-[var(--col-cyan)]" />
                            <h3 className="m-0 text-[0.95rem] text-[var(--col-text)]">No scheduled scans yet</h3>
                            <p className="mt-[0.4rem] mb-0 text-[0.78rem]">Create a weekly or monthly scan for a verified domain.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 gap-[0.9rem] max-[900px]:grid-cols-1">
                            {schedules.map((schedule) => {
                                const busy = workingId === schedule.id;
                                const domainName = domainNames.get(
                                    schedule.verified_domain_id,
                                ) ?? "Unknown domain";

                                return(
                                    <article key={schedule.id} 
                                        className={"flex min-w-0 flex-col gap-4 rounded-[0.75rem] border border-[var(--col-panel-border)] bg-[var(--col-panel)] p-4 " +
                                        "shadow-[var(--sh-sm)] transition-[border-color,transform,box-shadow] duration-[160ms] hover:-translate-y-px " +
                                        "hover:border-[var(--col-edge-hot)] hover:shadow-[var(--sh-glow-cyan)]"}
                                    >

                                        <div className="flex items-center justify-between gap-3">
                                            <div className="flex min-w-0 items-center gap-[0.65rem]">
                                                <span className={"inline-flex h-8 w-8 flex-none items-center justify-center rounded-[0.55rem] border " +
                                                "border-[rgba(43,216,245,0.24)] bg-[rgba(43,216,245,0.08)] text-[var(--col-cyan)]"}
                                                >
                                                    <Radar size = {18} />
                                                </span>
                                                <div className="min-w-0">
                                                    <h3 className={"m-0 overflow-hidden text-ellipsis whitespace-nowrap text-[0.92rem] " +
                                                    "text-[var(--col-text)]"}
                                                    >{domainName}
                                                    </h3>
                                                    <p className="mt-[0.15rem] mb-0 text-[0.7rem] text-[var(--col-muted)]">Active vulnerability scan</p>
                                                </div>
                                            </div>

                                            <span className={schedule.is_active ? 
                                                "flex-none rounded-full border border-[rgba(74,222,128,0.35)] bg-[rgba(74,222,128,0.08)] px-2 py-[0.28rem] " +
                                                "text-[0.64rem] font-[750] tracking-[0.06em] text-[var(--col-success)] uppercase"

                                                : "flex-none rounded-full border border-[rgba(245,200,66,0.35)] bg-[rgba(245,200,66,0.08)] px-2 py-[0.28rem] " +
                                                "text-[0.64rem] font-[750] tracking-[0.06em] text-[var(--col-yellow)] uppercase"}
                                            >
                                                {schedule.is_active ? "Active": "Paused"}
                                            </span>
                                        </div>

                                        <div className={"flex items-start gap-[0.55rem] rounded-[0.55rem] border border-[var(--col-edge)] " +
                                        "bg-[var(--col-panel-deep)] p-[0.7rem] text-[var(--col-cyan)]"}
                                        >
                                            <CalendarClock size={17} className="mt-[0.1rem] flex-none" />
                                            <div className="flex min-w-0 flex-col gap-[0.2rem]">
                                                <strong className="text-[0.78rem] text-[var(--col-text)]">
                                                    {recurrenceDescription(schedule)}
                                                </strong>
                                                <span className="text-[0.7rem] text-[var(--col-muted)]">{schedule.timezone}</span>
                                            </div>
                                        </div>

                                        <dl className="m-0 grid grid-cols-2 gap-[0.7rem] max-[700px]:grid-cols-1">
                                            <div className = "min-w-0">
                                                <dt className="text-[0.67rem] tracking-[0.04em] text-[var(--col-muted)] uppercase">Next run</dt>
                                                <dd className="mt-1 mb-0 overflow-hidden text-ellipsis text-[0.75rem] text-[var(--col-text)]">
                                                    {schedule.is_active ? formatDateTime(schedule.next_run_at) : "Paused"}
                                                </dd>
                                            </div>

                                            <div className = "min-w-0">
                                                <dt className="text-[0.67rem] tracking-[0.04em] text-[var(--col-muted)] uppercase">Last run</dt>
                                                <dd className="mt-1 mb-0 overflow-hidden text-ellipsis text-[0.75rem] text-[var(--col-text)]">
                                                    {formatDateTime(schedule.last_run_at)}
                                                </dd>
                                            </div>
                                        </dl>

                                        <div className={"mt-auto flex items-center justify-end gap-[0.45rem] border-t border-[var(--col-edge)] " +
                                        "pt-[0.8rem] max-[700px]:flex-col max-[700px]:items-stretch"}
                                        >
                                            <button type="button" className={`${secondaryButtonClass} max-[700px]:w-full`} 
                                                onClick={() => openEditForm(schedule)}
                                                disabled={busy}
                                            >
                                                <Edit3 size={15} />
                                                Edit
                                            </button>

                                            <button type="button" className={`${secondaryButtonClass} max-[700px]:w-full`} 
                                                onClick={() => void toggleSchedule(schedule)}
                                                disabled={busy}
                                            >
                                                {schedule.is_active ? (
                                                    <>
                                                        <Pause size={15} />
                                                        Pause
                                                    </>
                                                ): (
                                                    <>
                                                        <Play size={15} />
                                                        Resume
                                                    </>
                                                )}
                                            </button>

                                            <button type="button" className={dangerButtonClass} 
                                                onClick={() => void removeSchedule(schedule)}
                                                disabled={busy} aria-label={`Delete schedule for ${domainName}`}
                                            >
                                                <Trash2 size={15} />
                                            </button>
                                        </div>
                                    </article>
                                );
                            })}
                        </div>
                    )}
                </section>
            </div>
        </DashboardLayout>
    );
}

