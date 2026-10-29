import { NextRequest, NextResponse } from "next/server";
import { isValidEngagementId } from "@/lib/engagementsBackend";
import { proxyToRetestsApi } from "@/lib/retestsBackend";

export async function POST(
    request: NextRequest,
    { params }: { params: { id: string } },
) {
    const id = params.id;

    if (!isValidEngagementId(id)) {
        return NextResponse.json(
            { detail: "Invalid retest ID format." },
            { status: 400 },
        );
    }

    const formData = await request.formData();

    return proxyToRetestsApi(`/${id}/evidence`, {
        method: "POST",
        body: formData,
    });
}