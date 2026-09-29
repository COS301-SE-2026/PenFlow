import { NextResponse } from "next/server";
import { isValidEngagementId, proxyToEngagementsApi } from "@/lib/engagementsBackend";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    if (!isValidEngagementId(id)) {
        return NextResponse.json({ detail: "Invalid engagement ID format" }, { status: 400 });
    }
    return proxyToEngagementsApi(`/${id}/report`);
}