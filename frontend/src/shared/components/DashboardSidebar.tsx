"use client"

import Link from "next/link";
import { usePathname  } from "next/navigation"

const navItems = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Domains", href: "/domains" },
    { label: "Scans", href: "/scans" },
    { label: "Scheduled Scans", href: "/scheduled-scans" },
    { label: "Scan History", href: "/history" },
    { label: "Settings", href: "/settings" },
    { label: "Help", href: "/help" },
];


export default function DashboardSidebar() {

    const pathname = usePathname();

    return (   
        <aside className = "dashboard-sidebar">
            <Link href = "/dashboard" className = "dashboard-sidebar-brand">
                PENFLOW
            </Link>


            <nav aria-label = "Main Navigation">
                <ul>
                    { navItems.map((item) => {
                        const isActive = pathname === item.href ||
                                         pathname.startsWith(`${item.href}/`);
                        return (
                            <li key = {item.href}>
                                <Link href = {item.href} className = {
                                    isActive ? "dashboard-sidebar-link dashboard-sidebar-link-active" : 
                                               "dashboard-sidebar-link" }>
                                    {item.label}
                                </Link>
                            </li>
                        );
                    })}
                </ul>
            </nav>            
        </aside>
    );
}