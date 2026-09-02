import { authenticatedFetch } from "./authFetch";

const API_BASE = "/api/scan-schedules";

export type ScanScheduleFrequency = "weekly" | "monthly"
export type ScheduledScanType = "active_vulnerability"

export interface ScanSchedule {
    id: string;
    user_id: string;
    verified_domain_id: string;
    scan_type: ScheduledScanType;
    frequency: ScanScheduleFrequency;
    run_time: string;
    day_of_week: number | null;
    day_of_month: number | null;
    timezone: string;
    is_active: boolean;
    next_run_at: string;
    last_run_at: string | null;
    created_at: string;
    updated_at: string;
}

export interface CreateScanSchedule {
    verified_domain_id: string;
    scan_type?: ScheduledScanType;
    frequency: ScanScheduleFrequency;
    run_time: string;
    day_of_week: number | null;
    day_of_month: number | null;
    timezone: string;
}

export interface UpdateScanSchedule {
    frequency?: ScanScheduleFrequency;
    run_time?: string;
    day_of_week?: number | null;
    day_of_month?: number | null;
    timezone?: string;
    is_active?: boolean;
}

async function parseError(response: Response, fallback: string): Promise<Error> {
    const body = await response.json().catch(() => null);
    return new Error(
        typeof body?.detail === "string"
        ? body.detail : fallback,
    );
}

export async function listScanSchedules(): Promise<ScanSchedule[]> {
    const response = await authenticatedFetch(API_BASE);

    if(!response.ok) {
        throw await parseError(response, "Failed to load scheduled scans");
    }

    return response.json()
}

export async function getScanSchedule(scheduleId: string): Promise<ScanSchedule> {
    const response = await authenticatedFetch(
        `${API_BASE}/${scheduleId}`,
    );

    if(!response.ok) {
        throw await parseError(response, "Failed to load scan schedule");
    }

    return response.json()
}

export async function createScanSchedule(payload: CreateScanSchedule): Promise<ScanSchedule> {
    const response = await authenticatedFetch(API_BASE, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            ...payload,
            scan_type: "active_vulnerability",
        }),
    });

    if(!response.ok) {
        throw await parseError(response, "Failed to create scan schedule");
    }

    return response.json()
}

export async function updateScanSchedule(
    scheduleId: string,
    payload: UpdateScanSchedule,
): Promise<ScanSchedule> {
    const response = await authenticatedFetch(`${API_BASE}/${scheduleId}`, 
    {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
    });

    if(!response.ok) {
        throw await parseError(response, "Failed to update scan schedule");
    }

    return response.json()
}

export async function deleteScanSchedule(scheduleId: string): Promise<void> {
    const response = await authenticatedFetch(`${API_BASE}/${scheduleId}`,
        {
            method: "DELETE",
        },
    );

    if(!response.ok) {
        throw await parseError(response, "Failed to delete scan schedule");
    }
}