import { NextRequest } from "next/server";
import { proxyToEngagementsApi } from "@/lib/engagementsBackend";

export async function PATCH(request: NextRequest, { params }: {params: Promise<{ id: string }> }){
    const { id } = await params;
    const searchParams = request.nextUrl.searchParams.toString();
    const query = searchParams ? `?${searchParams}` : "";
    return proxyToEngagementsApi(`/${id}/messages/read${query}`, { method: "PATCH" });
}