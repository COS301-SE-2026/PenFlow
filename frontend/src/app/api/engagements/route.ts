import { NextRequest } from "next/server";
import { proxyToEngagementsApi } from "@/lib/engagementsBackend";

export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams.toString();
    const query = searchParams ? `?${searchParams}` : "";
    return proxyToEngagementsApi(`/engagements${query}`);
}