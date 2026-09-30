import { NextResponse } from "next/server";
import { isValidBrandId, proxyToBrandIntelligenceApi } from "@/lib/brandIntelligenceBackend";

export async function GET
(
    _request: Request,
    { params }: { params: Promise<{ domain_id: string }> },
)

{
    const { domain_id } = await params;
    if (!isValidBrandId(domain_id))
    {
        return NextResponse.json({ detail: "Invalid domain id" }, { status: 400 });
    }
    return proxyToBrandIntelligenceApi(`/domain/${domain_id}`);
}
