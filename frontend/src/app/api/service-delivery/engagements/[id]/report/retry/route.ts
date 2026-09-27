import { proxyToServiceDeliveryApi } from "@/lib/serviceDeliveryBackend";
//try generating the report again if report fails
export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    return proxyToServiceDeliveryApi(`/engagements/${id}/report/retry`, { method: "POST" });
}