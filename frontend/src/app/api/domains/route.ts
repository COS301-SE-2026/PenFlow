import {NextRequest} from "next/server";
import { proxyToDomainsApi } from "@/lib/domainsBackend";

export async function GET(req: NextRequest) {
    return proxyToDomainsApi(req.nextUrl.search);
}

export async function POST(req: NextRequest) {
    const body = await req.text();
    return proxyToDomainsApi("/", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body,
    });
}