import { Suspense } from "react";
import DashboardLayout from "@/shared/components/DashboardLayout";
import ScanProgress from "../scan_progress";

export default function ScanProgressPage() {
    return (
        <DashboardLayout>
            <Suspense fallback = {<p className="text-sm text-muted-foreground">Loading scan status...</p>}>
                <ScanProgress />
            </Suspense>
        </DashboardLayout>
    );
}