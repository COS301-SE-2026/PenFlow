"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Cog, Fingerprint, KeyRound, Layers, Loader2, Network, ScanSearch, Server, ShieldCheck, XCircle,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import styles from "./ScanConsoleSection.module.css";
import { validateDomain } from "@/lib/domainValidator";
import { postScanRequest, fetchScanStatus } from "@/lib/scanService";

type SourceDef = { name: string; key: string; icon: LucideIcon; angle: number; distance: number; color: string };
const SOURCES: SourceDef[] = [
  { name: "Shodan", key: "shodan", icon: Server, angle: 35, distance: 0.62, color: "var(--col-alert)" },
  { name: "HaveIBeenPwned", key: "hibp", icon: KeyRound, angle: 95, distance: 0.42, color: "var(--col-orange)" },
  { name: "URLScan.io", key: "urlscan", icon: ScanSearch, angle: 150, distance: 0.7, color: "var(--col-yellow)" },
  { name: "Wappalyzer", key: "wappalyzer", icon: Layers, angle: 205, distance: 0.5, color: "#c084fc" },
  { name: "crt.sh", key: "crt.sh", icon: ShieldCheck, angle: 255, distance: 0.66, color: "var(--col-cyan)" },
  { name: "WHOIS", key: "dns", icon: Fingerprint, angle: 300, distance: 0.38, color: "var(--col-blue)" },
  { name: "DNS", key: "dns", icon: Network, angle: 340, distance: 0.72, color: "var(--col-success)" },
];

const IDLE_BLIPS = [
  { angle: 60, distance: 0.55 },
  { angle: 140, distance: 0.35 },
  { angle: 230, distance: 0.7 },
  { angle: 315, distance: 0.5 },
];

const EXAMPLE_DOMAINS = ["example.com", "yourcompany.co.za", "shop.example.org", "mybusiness.io"];

const IDLE_SPEED = 40;
const SCANNING_SPEED = 150;

type SourceState = "pending" | "running" | "done" | "failed";
type ReportStep = "pending" | "running" | "done";

function blipPosition(angle: number, distance: number) {
  const radians = (angle * Math.PI) / 180;
  return { left: `${50 + Math.sin(radians) * distance * 50}%`, top: `${50 - Math.cos(radians) * distance * 50}%` };
}

function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function useTypedPlaceholder(active: boolean): string {
  const [text, setText] = useState("");
  const [cursor, setCursor] = useState(true);
  useEffect(() => {
    if (!active) return;
    if (prefersReducedMotion()) {
      setText(EXAMPLE_DOMAINS[0]);
      return;
    }
    let example = 0;
    let length = 0;
    let deleting = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = () => {
      const word = EXAMPLE_DOMAINS[example];
      if (!deleting) {
        length += 1;
        setText(word.slice(0, length));
        if (length === word.length) {
          deleting = true;
          timer = setTimeout(tick, 1600);
          return;
        }
        timer = setTimeout(tick, 90);
      } else {
        length -= 1;
        setText(word.slice(0, length));
        if (length === 0) {
          deleting = false;
          example = (example + 1) % EXAMPLE_DOMAINS.length;
          timer = setTimeout(tick, 400);
          return;
        }
        timer = setTimeout(tick, 40);
      }
    };
    timer = setTimeout(tick, 600);
    const blink = setInterval(() => setCursor(prev => !prev), 530);
    return () => {
      clearTimeout(timer);
      clearInterval(blink);
    };
  }, [active]);
  return `${text}${cursor ? "|" : " "}`;
}

export default function ScanConsoleSection() {
  const [domain, setDomain] = useState("");
  const [scannedDomain, setScannedDomain] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [reportReady, setReportReady] = useState(false);
  const [scanId, setScanId] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scanComplete, setScanComplete] = useState(false);
  const [progress, setProgress] = useState(0);
  const [sourceStates, setSourceStates] = useState<SourceState[]>(SOURCES.map(() => "pending"));
  const [reportStep, setReportStep] = useState<ReportStep>("pending");
  const router = useRouter();

  const scopeRef = useRef<HTMLDivElement>(null);
  const sweepRef = useRef<HTMLDivElement>(null);
  const scanningRef = useRef(false);
  scanningRef.current = scanning;

  const placeholder = useTypedPlaceholder(domain === "");
  const canScan = domain.trim().length > 2;

  useEffect(() => {
    if (prefersReducedMotion()) return;
    let frame = 0;
    let angle = 0;
    let speed = IDLE_SPEED;
    let last = performance.now();
    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const target = scanningRef.current ? SCANNING_SPEED : IDLE_SPEED;
      speed += (target - speed) * Math.min(1, dt * 1.5);
      const previous = angle;
      angle = (angle + speed * dt) % 360;
      if (sweepRef.current) sweepRef.current.style.transform = `rotate(${angle}deg)`;

      scopeRef.current?.querySelectorAll<HTMLElement>("[data-blip-angle]").forEach(blip => {
        if (blip.dataset.visible === "false") return;
        const at = Number(blip.dataset.blipAngle);
        const crossed = previous <= angle ? previous < at && at <= angle : at > previous || at <= angle;
        if (!crossed) return;
        const peak = Number(blip.dataset.peak ?? 1);
        const rest = Number(blip.dataset.rest ?? 0);
        blip.animate(
          [
            { opacity: rest, transform: "scale(0.6)" },
            { opacity: peak, transform: "scale(1.5)", offset: 0.06 },
            { opacity: peak * 0.9, transform: "scale(1)", offset: 0.25 },
            { opacity: rest, transform: "scale(1)" },
          ],
          { duration: 2600, easing: "ease-out" },
        );
      });
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, []);

  const onSubmit = async (e: { preventDefault(): void }) => {
    e.preventDefault();

    const result = validateDomain(domain);
    if (!result.valid) {
      setError(result.error);
      return;
    }

    try {
      setError(null);
      const { scan_id } = await postScanRequest({ domain: result.domain });
      setScanId(scan_id);
      setScannedDomain(result.domain);
      setSourceStates(SOURCES.map(() => "pending"));
      setReportStep("pending");
      setReportReady(false);
      setScanComplete(false);
      setProgress(0);
      setScanning(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Scan request failed");
    }
  };

  const handleViewReport = async () => {
    if (!scanId) {
      setError("No report yet — run a scan first");
      return;
    }

    try {
      const summary = await fetchScanStatus(scanId);

      if (
        summary.report_status?.status === "completed" &&
        summary.report_status?.pdf_path
      ) {
        router.push(`/report/${scanId}`);
        return;
      }

      setError("Report is still generating...");
    } catch {
      setError("Report is not ready yet...");
    }
  };

  useEffect(() => {
    if (!scanId || !scanning) return;

    const interval = setInterval(async () => {
      try {
        const live = await fetchScanStatus(scanId);

        setSourceStates(
          SOURCES.map((source): SourceState => {
            const state = live.sources.find(item => item.source_name === source.key)?.status;
            if (state === "failed") return "failed";
            if (["completed", "partial", "skipped"].includes(state ?? "")) return "done";
            if (state === "running") return "running";
            return "pending";
          })
        );
        setProgress(live.progress ?? 0);

        if (live.report_status?.status === "completed") {
          setReportStep("done");
          setReportReady(true);
          setScanComplete(true);
          setProgress(100);
          setScanning(false);
          clearInterval(interval);
          return;
        }

        if (live.status === "completed" || live.progress === 100) {
          setScanComplete(true);
          setReportStep("running");
        }
      } catch {
        setError("Unable to fetch scan progress");
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [scanId, scanning]);

  const runningSource = SOURCES.find((_, i) => sourceStates[i] === "running");
  let statusText = "Ready to scan";
  let statusTone: "idle" | "active" | "done" = "idle";
  if (reportReady) {
    statusText = "Scan complete";
    statusTone = "done";
  } else if (scanComplete) {
    statusText = "Building report...";
    statusTone = "active";
  } else if (scanning) {
    statusText = runningSource ? `Scanning ${runningSource.name}...` : `Scanning ${scannedDomain}...`;
    statusTone = "active";
  }
  const showProgress = scanning || scanComplete || reportReady;

  return (
    <section id="scan" className={styles.scanSection}>
      <div className={styles.consoleShell}>
        <h2 className={styles.consoleLabel}>SCAN YOUR DOMAIN NOW:</h2>
        <div className={styles.consoleTop}>
          <div className={styles.crPanel}>
            <div className={styles.crRadarWrap} aria-hidden="true">
              <div ref={scopeRef} className={styles.crScope}>
                <svg className={styles.crGrid} viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="16" />
                  <circle cx="50" cy="50" r="31" />
                  <line x1="50" y1="2" x2="50" y2="98" />
                  <line x1="2" y1="50" x2="98" y2="50" />
                  {Array.from({ length: 8 }, (_, i) => {
                    const radians = (i * 45 * Math.PI) / 180;
                    return (
                      <line
                        key={i}
                        x1={50 + Math.sin(radians) * 43} y1={50 - Math.cos(radians) * 43}
                        x2={50 + Math.sin(radians) * 49} y2={50 - Math.cos(radians) * 49}
                        className={styles.crTickMajor}
                      />
                    );
                  })}
                </svg>

                <div ref={sweepRef} className={styles.crSweep} />

                {IDLE_BLIPS.map(blip => (
                  <span
                    key={`idle-${blip.angle}`}
                    className={styles.crIdleBlip}
                    data-blip-angle={blip.angle}
                    data-visible={!showProgress}
                    data-peak={0.45}
                    data-rest={0}
                    style={blipPosition(blip.angle, blip.distance)}
                  />
                ))}

                {SOURCES.map((source, i) => {
                  const found = sourceStates[i] === "done" || sourceStates[i] === "failed";
                  return (
                    <span
                      key={source.name}
                      className={styles.crSourceBlip}
                      data-blip-angle={source.angle}
                      data-visible={found}
                      data-peak={1}
                      data-rest={0.55}
                      style={{ ...blipPosition(source.angle, source.distance), color: sourceStates[i] === "failed" ? "var(--col-alert)" : source.color }}
                    >
                      {found && <span className={styles.crBlipRing} />}
                    </span>
                  );
                })}

                {showProgress && (
                  <div className={styles.crCentre}>
                    <span className={styles.crPercent}>{progress}%</span>
                  </div>
                )}
              </div>
            </div>

            <p className={styles.crStatus} data-tone={statusTone} role="status">{statusText}</p>
          </div>

          <div className={styles.processPanel}>
            <div className={styles.crChips}>
              {SOURCES.map((source, i) => {
                const state = sourceStates[i];
                const Icon = state === "running" ? Loader2 : state === "failed" ? XCircle : source.icon;
                return (
                  <span key={source.name} className={styles.crChip} data-status={state}>
                    <Icon className={styles.crChipIcon} data-spin={state === "running"} aria-hidden="true" />
                    {source.name}
                  </span>
                );
              })}
              <span className={styles.crChip} data-status={reportStep}>
                {reportStep === "running"
                  ? <Loader2 className={styles.crChipIcon} data-spin="true" aria-hidden="true" />
                  : <Cog className={styles.crChipIcon} aria-hidden="true" />}
                Normalising
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
              placeholder={placeholder}
              value={domain}
              onChange={(e) => { setDomain(e.target.value); setError(null); }}
              aria-label="Domain to scan"
              autoCapitalize="off"
              autoCorrect="off"
              spellCheck={false}
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

        {error && <p className={styles.scanStatus} data-tone="error">{error}</p>}
      </div>
    </section>
  );
}