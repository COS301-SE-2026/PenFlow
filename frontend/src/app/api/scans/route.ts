import type { NextRequest } from "next/server";
import { proxyToPublicScansApi, proxyToScansApi } from "@/lib/scansBackend";

const LIST_PARAMS = ["limit", "offset", "scan_status"];

export async function GET(req: NextRequest) {
    const forwarded = new URLSearchParams();
    for (const key of LIST_PARAMS) {
        const value = req.nextUrl.searchParams.get(key);
        if (value !== null) forwarded.set(key, value);
    }
    const query = forwarded.toString();
    return proxyToScansApi(query ? `/?${query}` : "/");
}

export async function POST(req: Request) {
    const body = await req.text();
    return proxyToPublicScansApi("/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
    });
}