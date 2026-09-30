import { proxyServiceDeliveryBinary } from "@/lib/serviceDeliveryBackend";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string}> }) {
    const { id } = await params;
    return proxyServiceDeliveryBinary(`/reports/${id}/download`, {
        method:"GET",
    });
}