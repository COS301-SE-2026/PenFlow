import { NextRequest, NextResponse } from "next/server";
import { isValidEngagementId } from "@/lib/engagementsBackend";
import { proxyToRetestsApi } from "@/lib/retestsBackend";

export async function PATCH(
    request: NextRequest,
    {params}:{params:{id:string}}
){
    const id = params.id;
    if(!isValidEngagementId(id)){
        return NextResponse.json({detail: "Invalid engagement ID format"},{status:400});
    }
    const body = await request.text();
    return proxyToRetestsApi(`/${id}`, {
        method:"PATCH",
        headers: {"Content-type":"application/json"},
        body,
    });
}