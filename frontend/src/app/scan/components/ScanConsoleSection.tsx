"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import styles from "./ScanConsoleSection.module.css";
import { validateDomain } from "@/lib/domainValidator";   
import { postScanRequest,  fetchScanStatus} from "@/lib/scanService";  

const LEFT_SOURCES  = ["Shodan", "HaveIBeenPwned", "URLScan.io", "Hunter.io"];
const RIGHT_SOURCES = ["crt.sh", "WHOIS", "DNS"];
const SOURCES = [...LEFT_SOURCES, ...RIGHT_SOURCES, "Normalising"];
const SOURCE_MAPPINGS: Record<string, string> = {
  Shodan: "shodan",
  HaveIBeenPwned: "hibp",
  "URLScan.io": "urlscan",
  "Hunter.io": "hunter.io",
  "crt.sh": "crt.sh",
  WHOIS: "dns",
  DNS: "dns",
  Normalising: "normalising",
};

export default function ScanConsoleSection() {
  const [domain, setDomain] = useState("");
  const [status, setStatus] = useState("Ready to scan");
  const [reportReady, setReportReady] = useState(false);
  const [scanId, setScanId] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [sweeping, setSweeping] = useState(false);
  const [stepsDone, setStepsDone] = useState<boolean[]>(Array(SOURCES.length).fill(false));
  const router = useRouter();

  const canScan = domain.trim().length > 2;




    //the validation moves to  lib/domainvalidator and add scan service
  const onSubmit = async (e: { preventDefault(): void }) => {
    e.preventDefault();

    const result = validateDomain(domain);
    if (!result.valid) {
      setStatus(result.error);
      return;
    }

    try {
      const { scan_id } = await postScanRequest({ domain: result.domain });
      setScanId(scan_id);
      setStepsDone(Array(SOURCES.length).fill(false));
      setReportReady(false);
      setScanning(true);
      setSweeping(true);
      setStatus(`Scanning ${result.domain}...`);
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

      const summary = await fetchScanStatus(scanId);

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

  useEffect(() => {
    if (!scanId || !scanning) return;

    const interval = setInterval(async () => {
      try {
        const liveScanStatus = await fetchScanStatus(scanId);

        setStepsDone(SOURCES.map((source) => {
            if (source === "Normalising") {
              return liveScanStatus.status === "completed" || liveScanStatus.progress === 100;
            }

            const sourceName = SOURCE_MAPPINGS[source];
            return liveScanStatus.sources.some((item) =>
                item.source_name === sourceName &&
                ["completed", "failed", "partial"].includes(item.status)
            );
          })
        );

        if (liveScanStatus.report_status?.status === "completed") {
          setReportReady(true);
          setScanning(false);
          setSweeping(false);
          setStatus("Scan complete and report ready");
          clearInterval(interval);
          return;
        }

        if (liveScanStatus.status === "completed") {
          setStatus("Scan complete, generating report...");
        } else {
          setStatus(`Scanning... ${liveScanStatus.progress}% complete`);
        }
      } catch {
        setStatus("Unable to fetch scan progress");
      }

    }, 2000);
  
    return () => clearInterval(interval);
  }, [scanId, scanning]);

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
          <div className={styles.processCols}>
              <div className={styles.processCol}>
                {LEFT_SOURCES.map((source, i) => (
                  <span key={source} className={styles.processLabel} data-done={stepsDone[i]}>
                    {source}
                  </span>
                ))}
              </div>
              <div className={styles.processCol}>
                {RIGHT_SOURCES.map((source, i) => (
                  <span key={source} className={styles.processLabel} data-done={stepsDone[LEFT_SOURCES.length + i]}>
                    {source}
                  </span>
                ))}
                <span className={`${styles.processLabel} ${styles.normalisingLabel}`} data-done={stepsDone[SOURCES.length - 1]}>
                  Normalising
                </span>
              </div>
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
