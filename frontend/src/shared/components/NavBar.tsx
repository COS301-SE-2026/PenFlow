"use client";

import Link from "next/link";
import Image from "next/image";
import brocodeLogo from "@/app/images/images/BroCode logo.png";
import bluevisionLogo from "@/app/images/images/Bluevision logo.png";
import { useEffect, useState } from "react";

function isLoggedIn(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split("; ").some((c) => c.startsWith("logged_in="));
}

export default function NavBar() {
  //fix hydation error for login
  const [loggedIn,setLoggedIn] = useState(false);

  useEffect( ()=>{
    setLoggedIn(isLoggedIn());
  },[]);
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

      <div className="topnav">
        {!loggedIn && (
          <Link href="/login" className="nav-link">
            LOGIN
          </Link>
        )}
        {loggedIn && (
          <a href="/api/auth/logout" className="nav-link">
            LOGOUT
          </a>
        )}
        {!loggedIn && (
          <Link href="/" className="nav-link">
            HOME
          </Link>
        )}
        {!loggedIn && (
          <Link href="/#about" className="nav-link">
            ABOUT
          </Link>
        )}
        <Link href="/#scan" className="nav-link">
          SCAN
        </Link>
        {loggedIn && (
          <Link href="/history" className="nav-link">
            HISTORY
          </Link>
        )}
      </div>
    </nav>
  );
}
