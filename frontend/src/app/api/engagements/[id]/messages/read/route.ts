import { NextRequest, NextResponse } from "next/server";
import { isValidEngagementId, proxyToEngagementsApi } from "@/lib/engagementsBackend";

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    if (!isValidEngagementId(id)) {
        return NextResponse.json({ detail: "Invalid engagement ID format" }, { status: 400 });
    }
    const searchParams = request.nextUrl.searchParams.toString();
    const query = searchParams ? `?${searchParams}` : "";
    return proxyToEngagementsApi(`/${id}/messages/read${query}`, { method: "PATCH" });
}
