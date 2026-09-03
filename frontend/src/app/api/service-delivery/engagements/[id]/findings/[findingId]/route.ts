import { proxyToServiceDeliveryApi } from "@/lib/serviceDeliveryBackend";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string; findingId: string }> }) {
    const { id, findingId } = await params;
    return proxyToServiceDeliveryApi(`/engagements/${id}/findings/${findingId}`);
}
