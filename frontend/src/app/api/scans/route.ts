import {proxyToScansApi} from "@/lib/scansBackend";
export async function GET() {
    return proxyToScansApi("/");
}

export async function POST(req: Request) {
    const body = await req.text();
    return proxyToScansApi("/", {
        method: "POST",
        headers: { "Content-Type": "application/json"},
        body,
    });
}