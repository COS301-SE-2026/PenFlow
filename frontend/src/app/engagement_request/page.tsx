import DashboardLayout from "@/shared/components/DashboardLayout";
import { requirePageRole } from "@/lib/requirePageAccess";
import EngagementHome from "./engagement_request";


export default async function EngagementsPage() {
    await requirePageRole("client");

    return (
        <DashboardLayout>
            <EngagementHome />
        </DashboardLayout>
    );
}
