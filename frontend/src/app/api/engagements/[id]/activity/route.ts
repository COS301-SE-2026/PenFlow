import { NextRequest, NextResponse } from "next/server";
import { isValidEngagementId, proxyToEngagementsApi } from "@/lib/engagementsBackend";

export async function GET(
    _request: NextRequest,
    { params }: { params: { id: string } }
) {
    const id = params.id;
    if (!isValidEngagementId(id)) {
        return NextResponse.json({ detail: "Invalid engagement ID format" }, { status: 400});
    }
    return proxyToEngagementsApi(`/${id}/activity`);
}