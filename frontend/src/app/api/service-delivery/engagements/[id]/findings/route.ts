import { NextRequest } from "next/server";
import { proxyToServiceDeliveryApi } from "@/lib/serviceDeliveryBackend";

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    const searchParams = request.nextUrl.searchParams.toString();
    const query = searchParams ? `?${searchParams}` : "";
    return proxyToServiceDeliveryApi(`/engagements/${id}/findings${query}`);
}
