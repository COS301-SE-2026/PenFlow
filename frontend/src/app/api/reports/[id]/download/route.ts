import { proxyReportBinary } from "@/lib/reportsBackend";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    return proxyReportBinary(`/${id}/download`);
}
