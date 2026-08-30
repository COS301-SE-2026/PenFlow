"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import brocodeLogo from "@/app/images/images/BroCode logo.png";
import bluevisionLogo from "@/app/images/images/Bluevision logo.png";
import { Badge } from "@/shared/components/ui/badge";

type AdminNavItem = {
    label: string;
    href: string;
    badge?: number;
}

const adminNavItems: AdminNavItem[] = [
     { label: "Dashboard", href: "/admin/dashboard" },
    { label: "Engagements", href: "/admin/engagements", badge: 2 },
    { label: "Users", href: "/admin/users" },
    { label: "Audit Logs", href: "/admin/audit" },
];

export default function AdminSidebar() {
    const pathName = usePathname();

    return (
        <nav className="topbar">
            <div className="logoPanel">
            <Image
                src={bluevisionLogo}
                alt="Bluevision"
                width={80}
                height={48}
                style={{ width:"auto", height:48 }}
                />
                <div className="logoDivider" />
            <Image
                src={brocodeLogo}
                alt="BroCode"
                width={80}
                height={48}
                style={{ width: "auto", height: 48 }}
            />
            </div>
            <ul className="topnav-list">
                {adminNavItems.map((item) => {
                    const isActive = pathName === item.href || pathName.startsWith(`${item.href}/`);
                    return (
                        <li key={item.href}>
                            <Link
                                href={item.href}
                                className={isActive ? "nav-link nav-link-active" : "nav-link"}
                            >
                                {item.label}
                                {item.badge !== undefined && (
                                    <Badge className="ml-2">{item.badge}</Badge>
                                )}
                            </Link>
                        </li>
                    );
                })}
            </ul>
        </nav>
    );
}