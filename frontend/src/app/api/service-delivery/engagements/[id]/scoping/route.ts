import { proxyToServiceDeliveryApi } from "@/lib/serviceDeliveryBackend";

export async function PATCH(request: Request, { params }:{ params: Promise<{ id: string }>}) {
    const { id } = await params;
    const body = await request.text();
    return proxyToServiceDeliveryApi(`/engagements/${id}/scoping`, {
        method: "PATCH",
        headers: { "Content-Type":"application/json" },
        body,
    });
}
