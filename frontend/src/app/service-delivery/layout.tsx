import "@/shared/components/Dashboard.css";
import { requirePageRole } from "@/lib/requirePageAccess";
import ServiceDeliverySidebar from "@/shared/components/ServiceDeliverySidebar";

export default async function ServiceDeliverySectionLayout ({ children }: { children: React.ReactNode }){
    await requirePageRole("service_delivery");

    return (
        <div className="dashboard-layout">
            <ServiceDeliverySidebar/>
            <main className="dashboard-main">{children}</main>
        </div>
    );
}