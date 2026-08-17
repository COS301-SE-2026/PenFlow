//proxy file for email service
import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { isValidScanId, BACKEND_URL } from "@/lib/scansBackend";

export async function POST(req:Request,{params}:{ params: Promise<{scan_id:string
}>}){
    const {scan_id} = await params;
    if(!isValidScanId(scan_id)){
        return NextResponse.json({detail:"Invalid scan id"},{status:400})
    }

    const body = await req.json();
    const accessToken = (await cookies()).get("access_token")?.value;

     const response = await fetch(`${BACKEND_URL}/api/v1/scans/${scan_id}/email-report`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify(body),
        cache: "no-store",
    });
    const responseBody = await response.json().catch(() => ({}));
    return NextResponse.json(responseBody, { status: response.status });


}

