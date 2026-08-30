import { NextResponse } from "next/server";
import { setAuthCookies } from "@/lib/authSession";
import { authenticatedBackendFetch } from "@/lib/authenticatedBackend";
import { isValidScanId} from "@/lib/scansBackend";

export async function GET(_req:Request, {params} : {params: Promise<{scan_id: string}>}
) {
    const {scan_id} = await params;
    if(!isValidScanId(scan_id)) {
        return NextResponse.json({detail: "Invalid scan id"}, {status:400});
    }

    const { response, tokens } = await authenticatedBackendFetch(
        `/api/v1/scans/${scan_id}/pdf`,
    );

    if(!response.ok) {
        const body = await response.json()
        .catch(() => ({
            detail: "Failed to fetch report",
        }));

        const res = NextResponse.json(
            body,
            {
                status: response.status,
            },
        );

        if(tokens) {
            setAuthCookies(res, tokens);
        }

        return res;
    }

    const res = new NextResponse(
        response.body,
        {
            status: response.status,
            headers: {
                "Content-Type": response.headers.get(
                    "Content-Type",
                ) ?? "application/pdf",

                "Content-Disposition": response.headers.get(
                    "Content-Disposition",
                ) ?? `attachment; filename="PenFlow_Report_${scan_id}.pdf"`,
            },
        },
    );
    
    if(tokens) {
        setAuthCookies(res, tokens);
    }

    return res;
}