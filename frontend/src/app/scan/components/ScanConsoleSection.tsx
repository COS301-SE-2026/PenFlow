"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import styles from "./ScanConsoleSection.module.css";
import { validateDomain } from "@/lib/domainValidator";   
import { postScanRequest } from "@/lib/scanService";  

const SOURCES = ["crt.sh", "Shodan", "HaveIBeenPwned", "Wappalyser", "Normalising"];

export default function ScanConsoleSection() {
  const [domain, setDomain] = useState("");
  const [submittedDomain, setSubmittedDomain] = useState("");
  const [status, setStatus] = useState("Ready to scan");
  const [stepsDone, setStepsDone] = useState<boolean[]>(Array(SOURCES.length).fill(false));
  const [reportReady, setReportReady] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [sweeping, setSweeping] = useState(false);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const router = useRouter();

  const canScan = domain.trim().length > 2;

  const clearAllTimers = () => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  };

  const startScanSequence = (domainValue: string) => {
    clearAllTimers();
    setStepsDone(Array(SOURCES.length).fill(false));
    setReportReady(false);
    setScanning(true);
    setSweeping(true);
    setStatus(`Scanning ${domainValue}...`);

    SOURCES.forEach((_, index) => {
      const timer = setTimeout(() => {
        setStepsDone(prev => {
          const next = [...prev];
          next[index] = true;
          return next;
        });
        if (index === SOURCES.length - 1) {
          const reportTimer = setTimeout(() => {
            setReportReady(true);
            setScanning(false);
            setSweeping(false);
            setStatus("Scan complete — report ready");
          }, 1000);
          timersRef.current.push(reportTimer);
        }
      }, (index + 1) * 1000);
      timersRef.current.push(timer);
    });
  };

    //the validation moves to  lib/domainvalidator and add scan service
  const onSubmit = async (e: { preventDefault(): void }) => {
    e.preventDefault();

    const result = validateDomain(domain);
    if (!result.valid) {
      setStatus(result.error);
      return;
    }

    try {
      await postScanRequest(result.domain); //calls the backend api when validator is true
      setSubmittedDomain(result.domain);
      startScanSequence(result.domain);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Scan request failed";
      setStatus(message);
    }
  };

  const handleViewReport = () => {
    if (reportReady && submittedDomain) {
      router.push("/report");
    } else if (!submittedDomain) {
      setStatus("No report yet — run a scan first");
    } else {
      setStatus("Scan still in progress...");
    }
  };

  useEffect(() => () => clearAllTimers(), []);

  return (
    <section className={styles.scanSection}>
      <div className={styles.consoleShell}>
        <div className={styles.consoleTop}>
          <div className={styles.radarPanel} aria-hidden="true">
            <div className={styles.radarScope}>
              <div className={`${styles.radarRing} ${styles.r1}`} />
              <div className={`${styles.radarRing} ${styles.r2}`} />
              <div className={`${styles.radarRing} ${styles.r3}`} />
              {sweeping && (
                <>
                  <div className={styles.radarSweep} />
                  <span className={`${styles.radarDot} ${styles.dotCyan}`} />
                  <span className={`${styles.radarDot} ${styles.dotRed}`} />
                  <span className={`${styles.radarDot} ${styles.dotOrange}`} />
                  <span className={`${styles.radarDot} ${styles.dotBlue}`} />
                  <span className={`${styles.radarDot} ${styles.dotYellow}`} />
                </>
              )}
            </div>
          </div>

          <div className={styles.processPanel}>
            {SOURCES.map((source, i) => (
              <span key={source} className={styles.processLabel} data-done={stepsDone[i]}>
                {source}
              </span>
            ))}
            <Button
              type="button"
              variant="ghost"
              className={styles.viewReportButton}
              data-ready={reportReady}
              onClick={handleViewReport}
            >
              VIEW REPORT
            </Button>
          </div>
        </div>

        <form className={styles.consoleBottom} onSubmit={onSubmit}>
          <div className={styles.domainForm}>
            <input
              type="text"
              placeholder="YOUR DOMAIN HERE"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              aria-label="Domain input"
            />
            <Button type="submit" variant="ghost" size="icon" className={styles.searchButton} aria-label="Search">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="7" />
                <line x1="16.5" y1="16.5" x2="22" y2="22" />
              </svg>
            </Button>
          </div>

          <Button
            type="submit"
            variant="ghost"
            className={styles.scanNowButton}
            disabled={!canScan || scanning}
          >
            SCAN
          </Button>
        </form>

        <p className={styles.scanStatus}>{status}</p>
      </div>
    </section>
  );
}
