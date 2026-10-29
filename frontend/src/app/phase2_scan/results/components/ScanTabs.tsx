"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ChevronDown } from "lucide-react";
import{cn} from "@/lib/utils";

export default function ScanTabs({scanId, actions}:{scanId:string; actions?: React.ReactNode}) {
    const pathname = usePathname();
    const router = useRouter();
    const basePath = `/phase2_scan/results/${scanId}`;

    const scanTabs = [
        {label: "Overview", href: basePath},
        {label: "Security Analyst", href: `${basePath}/analyst`},
        {label: "Findings", href: `${basePath}/findings`},
        {label: "Assets", href: `${basePath}/assets`},
        {label: "Services", href: `${basePath}/services`},
        {label: "Activity", href: `${basePath}/activity`},
        {label: "Graph", href: `${basePath}/graph`},
    ];

    const isTabActive = (href: string) =>
        href === basePath ? pathname === basePath : pathname.startsWith(href);
    const activeHref = scanTabs.find((tab) => isTabActive(tab.href))?.href ?? basePath;

    return (
        <>
            <div className="sticky top-[60px] z-30 -mx-5 mt-3 hidden border-b border-brand-panel-border bg-[#050914] px-5 py-2 max-sm:block">
                <label className="relative block">
                    <span className="sr-only">Results section</span>
                    <select
                        value={activeHref}
                        onChange={(e) => router.push(e.target.value)}
                        className="min-h-10 w-full appearance-none rounded-lg border border-brand-panel-border bg-brand-panel-deep pr-9 pl-3 text-sm font-medium text-brand-cyan uppercase outline-none"
                    >
                        {scanTabs.map((tab) => (
                            <option key={tab.href} value={tab.href}>{tab.label}</option>
                        ))}
                    </select>
                    <ChevronDown aria-hidden="true" className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground" />
                </label>
            </div>

            <div className="relative mt-[22px] max-sm:hidden">
            <nav className={cn("flex flex-nowrap gap-4 overflow-x-auto border-b border-brand-panel-border lg:gap-[30px]", actions && "pr-[270px]")}>
                {scanTabs.map((tab) => {
                    const isActive = isTabActive(tab.href);

                    return (
                        <Link
                            key={tab.href}
                            href={tab.href}
                            className={cn("relative shrink-0 whitespace-nowrap px-1 py-3.5 text-xs font-medium uppercase no-underline transition-colors",
                                isActive ? "text-brand-cyan after:absolute after:bottom-[-1px] after:left-0 after:h-0.5 after:bg-brand-cyan after:content-['']"
                                : "text-muted-foreground hover:text-brand-cyan"
                    )}
                >{tab.label}</Link>
                );
                })}
            </nav>
            {actions && <div className="absolute right-0 bottom-2">{actions}</div>}
            </div>
        </>
    )
}