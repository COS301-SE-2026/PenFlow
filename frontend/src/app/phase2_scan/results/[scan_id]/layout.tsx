import DashboardLayout from "@/shared/components/DashboardLayout";
import ScanHeader from "../components/ScanHeader";
import ScanTabs from "../components/ScanTabs";

interface PhaseTwoScanLayoutProps {
    children: React.ReactNode;
    params: Promise<{scan_id: string}>;
}

export default async function PhaseTwoScanLayout({
    children,
    params,
}: PhaseTwoScanLayoutProps) {
    const {scan_id} = await params;
    return (
        <DashboardLayout>
            <div className="min-w-0">
                <ScanHeader scanId={scan_id} />
                <ScanTabs scanId={scan_id} />
                {children}
            </div>
        </DashboardLayout>
    );
}