import "@/shared/components/Dashboard.css";
import ServiceDeliverySidebar from "@/shared/components/ServiceDeliverySidebar";

export default function ServiceDeliverySectionLayout ({ children }: { children: React.ReactNode }){
    return (
        <div className="dashboard-layout">
            <ServiceDeliverySidebar/>
            <main className="dashboard-main">{children}</main>
        </div>
    );
}