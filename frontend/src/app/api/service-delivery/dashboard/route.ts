import { proxyToServiceDeliveryApi } from "@/lib/serviceDeliveryBackend";

export async function GET() {
    return proxyToServiceDeliveryApi("/dashboard");
}