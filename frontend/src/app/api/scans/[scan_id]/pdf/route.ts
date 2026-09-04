import { NextResponse } from "next/server";
import { fetchPublicScansApi, isValidScanId} from "@/lib/scansBackend";

export async function GET(_req:Request, {params} : {params: Promise<{scan_id: string}>}
) {
    const {scan_id} = await params;
    if(!isValidScanId(scan_id)) {
        return NextResponse.json({detail: "Invalid scan id"}, {status:400});
    }

    const response = await fetchPublicScansApi(`/${scan_id}/pdf`);

    if(!response.ok) {
        const body = await response.json()
        .catch(() => ({
            detail: "Failed to fetch report",
        }));


        return NextResponse.json(
            body,
            {
                status: response.status,
            },
        );
    }

    return new NextResponse(
        response.body,
        {
            status: response.status,
        },
    );
}