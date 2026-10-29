import DashboardLayout from "@/shared/components/DashboardLayout";
import ScanHeader from "../components/ScanHeader";
import PageHero from "@/shared/components/PageHero";

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
                <div className="max-sm:hidden">
                    <PageHero title="RESULTS" />
                </div>
                <ScanHeader scanId={scan_id} />
                {children}
            </div>
        </DashboardLayout>
    );
}