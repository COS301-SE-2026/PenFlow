import { NextResponse } from "next/server";
import { isValidBrandId, proxyToBrandIntelligenceApi } from "@/lib/brandIntelligenceBackend";

const valid_statuses = new Set
([
    "new",
    "under_review",
    "confirmed_impersonation",
    "false_positive",
    "resolved",
]);

export async function PATCH
(
    request: Request,
    { params }: { params: Promise<{ candidate_id: string }> },
)

{
    const { candidate_id } = await params;
    if (!isValidBrandId(candidate_id))
    {
        return NextResponse.json({ detail: "Invalid candidate id" }, { status: 400 });
    }

    const body: unknown = await request.json().catch(() => null);
    if
    (
        !body ||
        typeof body !== "object" ||
        !("status" in body) ||
        typeof body.status !== "string" ||
        !valid_statuses.has(body.status)
    )
    {
        return NextResponse.json({ detail: "Invalid candidate status" }, { status: 400 });
    }

    //send only the status that Jeandres backend accepts
    return proxyToBrandIntelligenceApi(`/candidate/${candidate_id}/status`, {method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: body.status })});
}
