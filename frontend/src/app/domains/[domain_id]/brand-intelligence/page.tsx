import DashboardLayout from "@/shared/components/DashboardLayout";
import BrandMonitoringOverview from "./BrandMonitoringOverview";

interface BrandIntelligencePageProps
{
    params: Promise<{ domain_id: string }>;
    searchParams: Promise<{ domain?: string }>;
}

export default async function BrandIntelligencePage
({
    params,
    searchParams,
}: BrandIntelligencePageProps)
{
    const [{ domain_id }, { domain }] = await Promise.all([params, searchParams]);

    return(
        <DashboardLayout>
            <BrandMonitoringOverview domainId={domain_id} domain={domain ?? null} />
        </DashboardLayout>
    );
}
