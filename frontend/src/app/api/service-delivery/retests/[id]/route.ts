import { proxyToServiceDeliveryApi } from "@/lib/serviceDeliveryBackend";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    return proxyToServiceDeliveryApi(`/retests/${id}`);
}
