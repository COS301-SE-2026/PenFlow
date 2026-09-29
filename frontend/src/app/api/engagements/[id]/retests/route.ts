import { NextRequest, NextResponse } from "next/server";
import { isValidEngagementId, proxyToEngagementsApi } from "@/lib/engagementsBackend";

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    if (!isValidEngagementId(id)) {
        return NextResponse.json({ detail: "Invalid engagement ID format" }, { status: 400 });
    }
    const body = await request.text();
    return proxyToEngagementsApi(`/${id}/retests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
    });
}