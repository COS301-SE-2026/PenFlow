import { NextRequest, NextResponse } from "next/server";
import { isValidEngagementId } from "@/lib/engagementsBackend"; 
import { proxyToFindingsApi } from "@/lib/findingsBackend";

export async function POST(
    request: NextRequest,
    {params}:{params:{id:string}}
){ 
    const id= params.id;
    if(!isValidEngagementId(id)){
        return NextResponse.json({detail: "Invalid engagement ID format"},{status:400});
    }
    const formData = await request.formData();
    return proxyToFindingsApi(`/${id}/evidence`, {
        method: "POST",
        body: formData,
}); 
}
