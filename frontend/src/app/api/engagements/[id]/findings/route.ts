import { NextRequest, NextResponse } from "next/server";
import { isValidEngagementId, proxyToEngagementsApi } from "@/lib/engagementsBackend";
export async function GET(
    request: NextRequest,
    { params } : { params: { id: string } }
){ 
    const id = params.id;
    if (!isValidEngagementId(id)) {
        return NextResponse.json({ detail: "Invalid engagement ID format" }, { status: 400 });
}
    const searchParams = request.nextUrl.searchParams.toString();
    const query = searchParams ? `?${searchParams}` : "";
    return proxyToEngagementsApi(`/${id}/findings${query}`);
}