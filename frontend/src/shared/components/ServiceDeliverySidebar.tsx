"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import penflowLogo from "@/app/images/images/PenFlow Logo.png";
import {listConversations } from "@/lib/serviceDeliveryService";
import NotificationMenu from "./NotificationMenu";

type ServiceDeliveryNavItem = 
    | { label: string; href : string; kind:"link"}
    | { label: string; href : string; kind:"external"}


const serviceDeliveryNavItems: ServiceDeliveryNavItem[] = [
    { label: "Dashboard", href: "/service-delivery/dashboard" , kind: "link"},
    { label: "Engagements", href: "/service-delivery/engagements", kind: "link" },
    { label: "Messages", href: "/service-delivery/messages", kind: "link" },
    { label: "Pentesters", href: "/service-delivery/pentesters" , kind: "link"},
    { label: "Audit Logs", href: "/service-delivery/audit" , kind: "link"},
    { label: "Logout", href: "/api/auth/logout", kind: "external"},
];

export default function ServiceDeliverySidebar() {
    const pathName = usePathname();
    const [badges, setBadges] = useState<Record<string, number>>({});

    useEffect(() => {
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
              src={penflowLogo}
              alt="PenFlow"
              className="penflowLogo"
              sizes="(max-width: 900px) 84px, 220px"
            />
          </div>            

            <ul className="topnav-list">
                <li>
                    <NotificationMenu />
                </li>
                 {serviceDeliveryNavItems.map((item) => {
                    const isActive = pathName === item.href || pathName.startsWith(`${item.href}/`);
                    const badge = badges[item.label];

                    if (
                        item.kind === "external"
                        && item.href === "/api/auth/logout"
                    ) {
                        return (
                            <li key={item.href}>
                                <form
                                    action="/api/auth/logout"
                                    method="post"
                                    className="m-0"
                                >
                                    <button
                                        type="submit"
                                        className="nav-link w-full cursor-pointer bg-transparent" text-left
                                    >
                                        {item.label}
                                    </button>
                                </form>
                            </li>
                        );
                    }      

                    if(item.kind === "external") { 
                    return (
                        <li key={item.href}>
                            <a href = {item.href} className="nav-link">
                                {item.label}
                            </a>
                        </li>
                    );
                }
                return (
                    <li key={item.href}>
                        <Link
                            href={item.href}
                            className={isActive ? "nav-link nav-link-active": "nav-link"}
                        >
                            {item.label}
                            {!!badge && (
                                <span className="float-right rounded-full bg-brand-blue px-1.5 py-0.5 text-[11px] font-semibold text-white">
                                    {badge}
                                </span>
                            )}
                        </Link>
                    </li>
                 );
            })}





            </ul>

            
        </nav>
     );
}
