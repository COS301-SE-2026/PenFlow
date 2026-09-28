import { Suspense } from "react";
import ScanGraph from "../../../scan_graph";

export default async function ScanResultsGraphPage({params}: {params: Promise<{scan_id: string}>}) {
    const {scan_id} = await params;
    return (
        <Suspense fallback={<p className="text-sm text-muted-foreground">Loading scan graph...</p>}>
            <ScanGraph scanId={scan_id} variant="embedded" />
        </Suspense>
    );
}