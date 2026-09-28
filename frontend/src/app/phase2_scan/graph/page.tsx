import { Suspense } from "react";
import DashboardLayout from "@/shared/components/DashboardLayout";
import ScanGraph from "../scan_graph";

export default function ScanGraphPage() {
    return (
        <DashboardLayout>
            <Suspense fallback={<p className="text-sm text-muted-foreground">Loading scan graph...</p>}>
                <ScanGraph />
            </Suspense>
        </DashboardLayout>
    );
}