"use client";
import { useState, useEffect, useRef } from "react";
import styles from "./OsintPanel.module.css";

const OSINT_SOURCES = [
  { name: "Shodan", desc: "Scans for open ports and exposed services accessible across the internet." },
  { name: "CRT.SH", desc: "Searches certificate transparency logs to discover subdomains and SSL certificates." },
  { name: "HAVEIBEENPWNED", desc: "Checks whether email addresses or credentials have appeared in known data breaches." },
  { name: "WHOIS", desc: "Retrieves domain registration records including ownership, registrar and expiry details." },
  { name: "URLSCAN.IO", desc: "Analyses URLs and web pages for suspicious content, scripts and external requests." },
  { name: "DNS", desc: "Queries DNS records to map subdomains, mail servers and name server configurations." },
  { name: "HUNTER.IO", desc: "Discovers publicly available email addresses associated with a domain." },
];

export default function OsintPanel() {
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  const [displayed, setDisplayed] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect( () => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  const handleClick = (idx: number) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setActiveIdx(idx);
    setDisplayed("");
    const full = `${OSINT_SOURCES[idx].name}:\n${OSINT_SOURCES[idx].desc}`;
    let i = 0;
    const tick = () => {
      i++;
      setDisplayed(full.slice(0,i));
      if (i < full.length) timerRef.current = setTimeout(tick, 16);
      };
      timerRef.current = setTimeout(tick, 16);
    };



return (
  <div className={styles.osintTerminal}>
    <div className={styles.terminalBar}>
      <span className={styles.termTitle}>WHAT WE USE TO SCAN YOUR SYSTEM</span>
    </div>

    <div className={styles.osintGrid}>
      {OSINT_SOURCES.map((src, i) => (
        <button
          key={src.name}
          className={styles.osintCard}
          data-active={activeIdx === i}
          onClick={() => handleClick(i)}
        >
          <span className={styles.osintDot} />
          {src.name}
        </button>
      ))}
    </div>

    <div className={styles.termOutput}>
      {displayed ? (
        <>
          <span>{displayed}</span>
          <span className={styles.termCursor}></span>
          </>
      ) : (
        <span className={styles.termPlaceholder}>{"// click a source to query"}</span>
      )}
    </div>
  </div>
);
}
