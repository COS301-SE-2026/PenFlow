import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export const BACKEND_URL = process.env.API_URL?? "http://localhost:3001";


export async function proxyToServiceDeliveryApi(path: string, init: RequestInit = {}): Promise<NextResponse> {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access_token")?.value;

    if(!accessToken){
        return NextResponse.json({ detail: "Not authenticated"}, { status: 401});
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/service-delivery${path}`, {
        ...init,
        headers:{
            ...init.headers,
            Authorization: `Bearer ${accessToken}`,
        },
        cache: "no-store",
    });

    if(response.status ===204){
        return new NextResponse(null,{ status: 204});
    }

    const body = await response.json().catch(() => null);
    if (response.status >=500) {
        console.error(`[service-delivery proxy] backend ${response.status} for ${path}:`, body);
        return NextResponse.json(
            { detail: "Something went wrong, Please try again later." },
            { status: response.status },
        );
    }
    return NextResponse.json(body, { status: response.status});

}

export async function proxyServiceDeliveryBinary(path: string): Promise<Response> {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access_token")?.value;

    if (!accessToken) {
        return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/service-delivery${path}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
        cache: "no-store",
    });

    if (!response.ok) {
        const body = await response.json().catch(() => null);
        return NextResponse.json(body ?? { detail: "Request failed." }, { status: response.status });
    }

    const headers = new Headers();
    const contentType = response.headers.get("content-type");
    const contentDisposition = response.headers.get("content-disposition");
    if (contentType) headers.set("content-type", contentType);
    if (contentDisposition) headers.set("content-disposition", contentDisposition);

    return new Response(response.body, { status: response.status, headers });
}