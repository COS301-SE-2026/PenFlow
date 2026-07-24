"use client";

import Link from "next/link";
import Image from "next/image";

import { usePathname} from "next/navigation";
import brocodeLogo from "@/app/images/images/BroCode logo.png";
import bluevisionLogo from "@/app/images/images/Bluevision logo.png";

function isLoggedIn(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split("; ").some((c) => c.startsWith("logged_in="));
}

type NavItem = 
  | { label: string; href: string; kind: "link"}
  | { label: string; href: string; kind: "external"}
  | { label: string; kind: "disabled"};

  const loggedInNavItems: NavItem[] = [
    { label: "Home", href: "/", kind: "link"},
    { label: "Dashboard", href: "/dashboard", kind: "link"},
    { label: "Domains", href: "/domains", kind: "link"},
    { label: "Scans", href: "/phase2_scan", kind: "link"},
    { label: "Scheduled Scans", href: "/scheduled-scans", kind: "link"},
    { label: "Scan History", href: "/history", kind: "link"},
    { label: "Old History", href: "/history", kind: "link"},
    { label: "Settings", href: "/settings", kind: "link"},
    { label: "Help", href: "/help", kind: "link"},
    { label: "Logout", href: "/api/auth/logout", kind: "external"},
  ];

export default function NavBar() {
  const loggedIn = isLoggedIn();
  const pathName = usePathname();

  return (
    <nav className = "topbar">
      <div className = "logoPanel">
        <Image
          src = {bluevisionLogo}
          alt = "Bluevision"
          width = {80}
          height = {48}
          style = {{width: "auto", height: 48}}
          />
          <div className="logoDivider" />
          <Image
            src = {brocodeLogo}
            alt = "BroCode"
            width = {80}
            height = {48}
            style = {{ width: "auto", height: 48}}
            />
      </div>

      {loggedIn ? (
        <ul className = "topnav-list">
          {loggedInNavItems.map((item) => {
            if (item.kind === "external") {
              return (
                <li key={item.label}>
                  <a href={item.href} className="nav-link">
                    {item.label}
                  </a>
                </li>
              );
            }

            if(item.kind === "disabled") {
              return (
                <li key={item.label}>
                  <span className="nav-link nav-link-disabled" aria-disabled="true">
                    {item.label}
                  </span>
                </li>
              );
            }

            const isActive = pathName === item.href || (item.href !== "/" && pathName.startsWith(`${item.href}/`));

            return ( 
              <li key={item.href}>
                <Link href = {item.href} className={isActive ? "nav-link nav-link-active" : "nav-link"}>
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="topnav">
          <Link href = "/login" className="nav-link">
            LOGIN
          </Link>
          <Link href = "/" className="nav-link">
            HOME
          </Link>
          <Link href = "/#about" className="nav-link">
            ABOUT
          </Link>
          <Link href = "/#scan" className="nav-link">
            SCAN
          </Link>
        </div>
      )
    }
    </nav>
  );
}