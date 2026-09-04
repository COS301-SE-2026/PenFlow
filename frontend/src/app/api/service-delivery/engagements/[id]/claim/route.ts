import { proxyToServiceDeliveryApi } from "@/lib/serviceDeliveryBackend";

export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    return proxyToServiceDeliveryApi(`/engagements/${id}/claim`,{ method: "POST"});
}
