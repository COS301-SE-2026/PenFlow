import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export const BACKEND_URL = process.env.API_URL ?? "http://localhost:3001";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isValidEngagementId(value: string): boolean {
    return UUID_PATTERN.test(value);
}
