import { NextResponse } from "next/server";
import { isValidScanId , proxyToPublicScansApi} from "@/lib/scansBackend";

export async function GET(
    _req: Request,
    {params} : {params: Promise<{scan_id: string}>}
) {
    const{scan_id} = await params;
    if(!isValidScanId(scan_id)) {
        return NextResponse.json({detail: "Invalid scan id"}, {status: 400});
    }
    return proxyToPublicScansApi(`/${scan_id}/status`);
}
