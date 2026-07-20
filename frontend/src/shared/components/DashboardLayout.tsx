import "./Dashboard.css"
import DashboardSidebar from "./DashboardSidebar";

interface DashboardLayoutProperty {
    children: React.ReactNode;
}

export default function DashboardLayout({
    children,
}: DashboardLayoutProperty) {
    return (
        <div className = "dashboard-layout">
            <DashboardSidebar />

            <main className = "dashboard-main">
                {children}
            </main>
        </div>
    );
}