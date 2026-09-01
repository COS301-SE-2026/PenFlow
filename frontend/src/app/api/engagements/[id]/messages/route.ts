import { NextRequest } from "next/server";
import { proxyToEngagementsApi } from "@/lib/engagementsBackend";

export async function  GET(request: NextRequest, { params }: {params: Promise<{ id: string }> }) {
    const { id } = await params;
    const searchParams =request.nextUrl.searchParams.toString();
    const query = searchParams ? `?${searchParams}` : "" ;
    return proxyToEngagementsApi(`/${id}/messages${query}`);
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ id:string}>}){
    const { id } = await params;
    const body = await request.text();
    return proxyToEngagementsApi(`/${id}/messages`,{
        method: "POST",
        headers: { "Content-Type": "application/json"},
        body,
    });
}