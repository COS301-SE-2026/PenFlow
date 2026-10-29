"use client";

import { useEffect, useState } from "react";

export const MOBILE_NAV_BREAKPOINT_PX = 900;

export function useIsMobileNav(): boolean {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const query = window.matchMedia(`(max-width: ${MOBILE_NAV_BREAKPOINT_PX}px)`);
    const update = () => setIsMobile(query.matches);

    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  return isMobile;
}