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

    
}