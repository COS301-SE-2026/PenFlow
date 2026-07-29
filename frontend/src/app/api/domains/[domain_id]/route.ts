import { NextResponse } from "next/server";
import { isValidDomainId, proxyToDomainsApi } from "@/lib/domainsBackend";
export async function DELETE(
    _req: Request,{params}: {params: Promise<{domain_id: string}>}
){
    const {domain_id} = await params;
    if (!isValidDomainId(domain_id)) {
        return NextResponse.json({detail: "Invalid domain id"}, {status:400});
    }
    return proxyToDomainsApi(`/${domain_id}`, {method: "DELETE"});
}