import { proxyToServiceDeliveryApi } from "@/lib/serviceDeliveryBackend";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    const body = await request.text();
    return proxyToServiceDeliveryApi(`/engagements/${id}/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
    });
}
