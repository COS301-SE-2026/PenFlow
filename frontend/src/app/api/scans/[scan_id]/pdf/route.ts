import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { isValidScanId, BACKEND_URL } from "@/lib/scansBackend";

export async function GET(_req:Request, {params} : {params: Promise<{scan_id: string}>}
) {
    const {scan_id} = await params;
    if(!isValidScanId(scan_id)) {
        return NextResponse.json({detail: "Invalid scan id"}, {status:400});
    }

    const accessToken = (await cookies()).get("access_token")?.value;
    const response = await fetch(`${BACKEND_URL}/api/v1/scans/${scan_id}/pdf`, {
        headers: accessToken ? {Authorisation: `Bearer ${accessToken}`} : {},
        cache: "no-store",
    });

    if(!response.ok) {
        const body = await response.json().catch(() => ({detail: "Failed to fetch report"}));
        return NextResponse.json(body, {status: response.status});
    }

    return new NextResponse(response.body, {
        status: 200,
        headers: {
            "Content-Disposition" : response.headers.get("Content-Disposition") ??
            `attachment; filename="PenFlow_Report_${scan_id}.pdf"`,
        },
    });
    
}