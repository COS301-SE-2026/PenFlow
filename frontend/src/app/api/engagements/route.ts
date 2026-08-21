import { NextRequest } from "next/server";
import { proxyToEngagementsApi } from "@/lib/engagementsBackend";

export async function POST(req: NextRequest) {
    const body = await req.text();
    return proxyToEngagementsApi("/",{
        method: "POST",
        headers: {"Content-type" : "application/json"},
        body,
    });
}
