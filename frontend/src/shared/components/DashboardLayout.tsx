import "./Dashboard.css"
import NavBar from "./NavBar";

interface DashboardLayoutProperty {
    children: React.ReactNode;
}

export default function DashboardLayout({
    children,
}: DashboardLayoutProperty) {
    return (
        <div className = "dashboard-layout">
            <Navbar />

            <main className = "dashboard-main">
                {children}
            </main>
        </div>
    );
}