import { NextRequest } from "next/server";
import { proxyToServiceDeliveryApi } from "@/lib/serviceDeliveryBackend";

export async function GET(request: NextRequest){
    const searchParams = request.nextUrl.searchParams.toString();
    const query = searchParams ? `?${searchParams}` : "";
    return proxyToServiceDeliveryApi(`/audit${query}`);
}