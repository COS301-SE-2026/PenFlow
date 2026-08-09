"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import{cn} from "@/lib/utils";

export default function ScanTabs({scanId}:{scanId:string}) {
    const pathname = usePathname();
    const basePath = `/phase2_scan/results/${scanId}`;

    const scanTabs = [
        {label: "Overview", href: basePath},
        {label: "Findings", href: `${basePath}/findings`},
        {label: "Assets", href: `${basePath}/assets`},
        {label: "Services", href: `${basePath}/services`},
        {label: "Activity", href: `${basePath}/activity`},
    ];

    return (
        <nav className="mt-[22px] flex gap-[30px] border-b border-brand-panel-border">
            {scanTabs.map((tab) => {
                const isOverview = tab.href === basePath && pathname === basePath;
                const isNestedTab = tab.href !== basePath && pathname.startsWith(tab.href);
                const isActive = isOverview || isNestedTab;

                return (
                    <Link   
                        key={tab.href}
                        href={tab.href}
                        className={cn("relative px-1 py-3.5 text-xs font-medium uppercase no-underline transition-colors",
                            isActive ? "text-brand-cyan after:absolute after:bottom-[-1px] after:left-0 after:h-0.5 after:bg-brand-cyan after:content-['']"
                            : "text-muted-foreground hover:text-brand-cyan"
                )}
            >{tab.label}</Link>
            );
            })}
        </nav>
    )
}