import "@/shared/components/Dashboard.css"
import AdminSidebar from "@/shared/components/AdminSidebar"

export default function AdminLayout({ children }: { children: React.ReactNode }){
    return (
            <div className="dashboard-layout">
                <AdminSidebar/>      
                 <main className="dashboard-main">{children}</main>          
            </div>     
    );
}