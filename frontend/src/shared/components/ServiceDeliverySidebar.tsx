"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import brocodeLogo from "@/app/images/images/BroCode logo.png";
import bluevisionLogo from "@/app/images/images/Bluevision logo.png";
import SidebarProfileFooter from "@/shared/components/SidebarProfileFooter";
import { getDashboard, listConversations } from "@/lib/serviceDeliveryService";

type ServiceDeliveryNavItem = {
    label: string;
    href: string;
};

const serviceDeliveryNavItems: ServiceDeliveryNavItem[] = [
    { label: "Dashboard", href: "/service-delivery/dashboard" },
    { label: "Engagements", href: "/service-delivery/engagements" },
    { label: "Messages", href: "/service-delivery/messages" },
    { label: "Pentesters", href: "/service-delivery/pentesters" },
    { label: "Audit Logs", href: "/service-delivery/audit" },
];

export default function ServiceDeliverySidebar() {
    const pathName = usePathname();
    const [badges, setBadges] = useState<Record<string, number>>({});

    useEffect(() => {
        getDashboard()
            .then((dashboard) => setBadges((prev) => ({ ...prev, Engagements: dashboard.counts.needs_attention })))
            .catch(console.error);
        listConversations()
            .then((res) => {
                const unread = res.items.reduce((sum, c) => sum + c.unread_count, 0);
                setBadges((prev) => ({ ...prev, Messages: unread }));
            })
            .catch(console.error);
    }, []);
     return (
        <nav className="topbar">
            <div className="logoPanel">
                <Image
                    src={bluevisionLogo}
                    alt="Bluevision"
                    width={80}
                    height={48}
                    style={{ width: "auto", height: 48 }}
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
                 {serviceDeliveryNavItems.map((item) => {
                    const isActive = pathName === item.href || pathName.startsWith(`${item.href}/`);
                    const badge = badges[item.label];
                    return (
                        <li key={item.href}>
                            <Link
                                href={item.href}
                                className={isActive ? "nav-link nav-link-active" : "nav-link"}
                            >
                                {item.label}
                                {!!badge&& (
                                    <span className="float-right rounded-full bg-brand-blue px-1.5 py-0.5 text-[11px] font-semibold text-white">
                                        {badge}
                                    </span>
                                )}
                            </Link>
                        </li>
                    );
                })}

            </ul>
            <SidebarProfileFooter name="Maya Chen" role="Service Delivery" />
        </nav>
     );
}
