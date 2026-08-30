import { NextRequest } from "next/server";
import { proxyToEngagementsApi } from "@/lib/engagementsBackend";

export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams.toString();
    const query = searchParams ? `?${searchParams}` : "";
    return proxyToEngagementsApi(query);
}
export async function POST(req: NextRequest) {
    const body = await req.text();
    return proxyToEngagementsApi("/",{
        method: "POST",
        headers: {"Content-type" : "application/json"},
        body,
    });
}
