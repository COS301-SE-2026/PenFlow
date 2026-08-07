"use client";

import Link from "next/link";
import Image from "next/image";

import { usePathname} from "next/navigation";
import brocodeLogo from "@/app/images/images/BroCode logo.png";
import bluevisionLogo from "@/app/images/images/Bluevision logo.png";
import { useEffect, useState } from "react";
import { getHelpTopics } from "../helpContext";
import type { HelpTopic } from "../helpContext";
import HelpTopicModal from "./HelpTopicModal";

function isLoggedIn(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split("; ").some((c) => c.startsWith("logged_in="));
}

type NavItem = 
  | { label: string; href: string; kind: "link"}
  | { label: string; href: string; kind: "external"}
  | { label: string; kind: "disabled"}
  | { label: string; kind: "help"};

  const loggedInNavItems: NavItem[] = [
    { label: "Home", href: "/", kind: "link"},
    //{ label: "Dashboard", href: "/dashboard", kind: "link"},
    { label: "Domains", href: "/domains", kind: "link"},
    { label: "Scans", href: "/phase2_scan", kind: "link"},
    //{ label: "Scheduled Scans", href: "/scheduled-scans", kind: "link"},
    { label: "Scan History", href: "/history", kind: "link"},
    //{ label: "Settings", href: "/settings", kind: "link"},
    { label: "Help", kind: "help"},
    { label: "Pentesting", href: "/pentesting/engagement", kind: "link"},
    { label: "Logout", href: "/api/auth/logout", kind: "external"},
  ];

  const pentestingNavItems: NavItem[] = [
    {label: "Home", href: "/", kind: "link"},
    {label: "Live Engagement", href: "/pentesting/engagement", kind: "link"},
    { label: "Help", kind: "help"},
    { label: "Logout", href: "/api/auth/logout", kind: "external"},
  ]

export default function NavBar() {
  //fix hydation error for login
  const [loggedIn,setLoggedIn] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const pathName = usePathname();
  const HelpTopics = getHelpTopics(pathName);
  const [activeTopic, setActiveTopic] = useState<HelpTopic | null>(null);
  const navItems = pathName.startsWith("/pentesting") ? pentestingNavItems : loggedInNavItems;

  useEffect( ()=>{
    setLoggedIn(isLoggedIn());
  },[]);
  return (
    <>
    <nav className = "topbar">
      <div className={`navFlip${helpOpen? " navFlipped": ""}`}>
        <div className="navFace navFaceFront">
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
          {navItems.map((item) => {
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

            if (item.kind === "help") {
              return (
                <li key={item.label}>
                  <button
                    type="button"
                    className="nav-link nav-link-help"
                    onClick={() => setHelpOpen(true)}
                  >
                    {item.label}
                  </button>
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
      )}
      </div>
    

    <div className="navFace navFaceBack">
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
      <div className="helpBackHeader">
        <button
          type = "button"
          className="helpBackBtn"
          onClick={() => setHelpOpen(false)}
          aria-label="Back to navigation"
        >
          &larr; Back
        </button>
        <span className="helpBackTitle">Help</span>
      </div>
      
      {HelpTopics.length > 0 ? (
        <ul className="helpTopicList">
          {HelpTopics.map((topic) => (
            <li key={topic.id}>
              <button
                type = "button"
                className = "helpTopicBtn"
                onClick={() => setActiveTopic(topic)}
              >
                {topic.title}
              </button>
            </li>
          ))}
        </ul>
      ): (
        <p className="helpEmpty">No help topics for this page.</p>
      )}

    </div>
    </div>
    </nav>
    <HelpTopicModal topic = {activeTopic} onClose={()=>setActiveTopic(null)} />
    </>
  );
}
