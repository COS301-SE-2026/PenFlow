"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import styles from "./ScanConsoleSection.module.css";
import { validateDomain } from "@/lib/domainValidator";
import { postScanRequest, fetchScanSummary } from "@/lib/scanService";

type ScanState = "idle" | "scanning" | "complete";

export default function ScanConsoleSection() {
  const [domain, setDomain] = useState("");
  const [status, setStatus] = useState("Ready to scan");
  const [reportReady, setReportReady] = useState(false);
  const [scanId, setScanId] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [sweeping, setSweeping] = useState(false);
  const [scanState, setScanState] = useState<ScanState>("idle");
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const router = useRouter();

  const canScan = domain.trim().length > 2;

  const stopPolling = () => {
    if (pollingRef.current != null) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
  }
  };

  const startPolling = (id: string) => {
    stopPolling();
    pollingRef.current = setInterval(async () => {
      try {
        const summary = await fetchScanSummary(id);
        const done =
          summary.scan_summary?.status === "completed" || 
          (summary.report_status?.status === "completed" && summary.report_status?.pdf_path);
        if (done) {
          stopPolling();
          setReportReady(true);
          setScanning(false);
          setSweeping(false);
          setScanState("complete");
          setStatus("Scan complete: report ready");
        }
      } catch{

      }
    }, 2000);
  };

  const onSubmit = async (e: { preventDefault(): void }) => {
    e.preventDefault();

    const result = validateDomain(domain);
    if (!result.valid) {
      setStatus(result.error);
      return;
    }

    try {
      const { scan_id } = await postScanRequest(result.domain);
      setScanId(scan_id);
      setReportReady(false);
      setScanning(true);
      setSweeping(true);
      setScanState("scanning");
      setStatus(`Scanning ${result.domain}...`);
      startPolling(scan_id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Scan request failed";
      setStatus(message);
    }
  };

  const handleViewReport = async () => {
    if (!scanId) {
      setStatus("No report yet — run a scan first");
      return;
    }

    try {
      setStatus("Checking report status...");

      const summary = await fetchScanSummary(scanId);

      if (
        summary.report_status?.status === "completed" &&
        summary.report_status?.pdf_path
      ) {
        router.push(`/report/${scanId}`);
        return;
      }

      setStatus("Report is still generating...");
    } catch {
      setStatus("Report is not ready yet...");
    }
  };

  useEffect(() => () => stopPolling(), []);

  return (
    <section id="scan" className={styles.scanSection}>
      <div className={styles.consoleShell}>
        <h2 className={styles.consoleLabel}>SCAN YOUR DOMAIN NOW:</h2>
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
            <div className={styles.scanningBox}>
              <span className={styles.scanningText} data-state={scanState}>
                SCANNING
              </span>
            </div>
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
