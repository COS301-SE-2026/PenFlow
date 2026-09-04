//proxy file for email service
import { NextResponse } from "next/server";
import { isValidScanId, proxyToPublicScansApi } from "@/lib/scansBackend";

export async function POST(req:Request,{params}:{ params: Promise<{scan_id:string
}>}){
    const {scan_id} = await params;
    if(!isValidScanId(scan_id)){
        return NextResponse.json({detail:"Invalid scan id"},{status:400})
    }

    const body = await req.json();

    return proxyToPublicScansApi(`/${scan_id}/email-report`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });
}

