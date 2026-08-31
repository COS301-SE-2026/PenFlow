import { NextRequest, NextResponse } from "next/server";
import { isValidEngagementId } from "@/lib/engagementsBackend";
import { proxyToFindingsApi } from "@/lib/findingsBackend";

export async function PATCH(
    request: NextRequest,
    {params}:{params:{id:string}}
){
    const id = params.id;
    if(!isValidEngagementId(id)){
        return NextResponse.json({detail: "Invalid engagement ID format"},{status:400});
    }
    const body = await request.text();
    return proxyToFindingsApi(`/${id}`, {
        method:"PATCH",
        headers: {"Content-type":"application/json"},
        body,
    });
}

export async function DELETE(
    _request:Request,
    {params}:{params:{id:string}}
){
    const id = params.id;
    if(!isValidEngagementId(id)){
        return NextResponse.json({detail: "Invalid engagement ID format"},{status:400});
    }
    return proxyToFindingsApi(`/${id}`,{method: "DELETE"});
}
