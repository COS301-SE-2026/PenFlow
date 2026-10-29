"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { JSAnimation, Timeline } from "animejs";
import Link from "next/link";
import { AlertTriangle, ArrowRight, Bug, Check, ChevronDown, Download, Globe, Loader2, Mail, Radar, ShieldAlert, ShieldCheck, Target, type LucideIcon } from "lucide-react";
import { useParams } from "next/navigation";
import NavBar from "@/components/NavBar";
import { fetchScanSummary, getReportPdfUrl, SEVERITY_COLORS, sendReportEmail } from "@/lib/scanService";
import type { ExecutiveSummary, TopFinding } from "@/lib/scanService";
import { formatDateTime, formatDateWithYear, formatEnumLabel } from "@/lib/engagementFormat";
import { cn } from "@/lib/utils";
import { RiskGauge } from "@/app/phase2_scan/results/components/ScanResultsOverview";
import styles from "./report.module.css";

function riskFor(counts: ExecutiveSummary["risk_snapshot"]) {
  const score = Math.min(100, counts.critical_count * 25 + counts.high_count * 15 + counts.medium_count * 5 + counts.low_count);
  if (score >= 70) return { score, level: "High", color: "#ef4444" };
  if (score >= 40) return { score, level: "Medium", color: "#facc15" };
  return { score, level: "Low", color: "#4ade80" };
}

function verdict(counts: ExecutiveSummary["risk_snapshot"]): string {
  const urgent = counts.critical_count + counts.high_count;
  if (urgent > 0) return `${urgent} critical or high-severity issue${urgent === 1 ? " needs" : "s need"} attention.`;
  if (counts.medium_count > 0) return `No critical or high issues. ${counts.medium_count} medium-severity issue${counts.medium_count === 1 ? "" : "s"} to review.`;
  if (counts.total_findings > 0) return "Only low-severity findings. Nothing urgent.";
  return "No issues were found in this scan.";
}

const SOURCE_LABELS: Record<string, string> = {
  hibp: "Breach data",
  dns: "DNS",
  tls: "TLS",
  cve: "CVE database",
  http_security: "HTTP headers",
  https_security: "HTTPS headers",
};
const sourceLabel = (source: string) => SOURCE_LABELS[source.toLowerCase()] ?? formatEnumLabel(source);

function duration(start: string | null, end: string | null): string | null {
  if (!start || !end) return null;
  const seconds = Math.max(0, Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

type IntroPhase = "pending" | "off" | "loading" | "playing" | "done";
const INTRO_HIDDEN = "group-data-[intro=playing]/report:opacity-0";
const introSeenKey = (scanId: string) => `penflow:report-intro:${scanId}`;
const GAUGE_WIDTH = 180;
const ASSET_TYPE_COLOR: Record<string, string> = { subdomain: "#2bd8f5", ipv4: "#a78bfa", ipv6: "#f472b6", ip: "#a78bfa", email: "#facc15" };
const assetTypeColor = (type: string) => ASSET_TYPE_COLOR[type.toLowerCase()] ?? "#94a3b8";
const INTRO_SPEED = 1.4;
const HOLD_AT_ZERO_MS = 2000;
const HOLD_AT_SCORE_MS = 1000;
const HOLD_AFTER_REVEAL_MS = 1000;
const STEP_MS = 260 * INTRO_SPEED;
const MAX_STEPPED_COUNT = 12;

function constantThenSettle(units: number) {
  const split = (units - 1) / (units + 1);
  const covered = (units - 1) / units;
  return (x: number) => {
    if (x <= split) return split === 0 ? 0 : (covered * x) / split;
    const local = (x - split) / (1 - split);
    return covered + (1 - covered) * (1 - (1 - local) ** 2);
  };
}

function riskColorFor(score: number): string {
  return score >= 70 ? "#ef4444" : score >= 40 ? "#facc15" : "#4ade80";
}

function CollapsibleCard({ title, aside, intro, className, children }: Readonly<{ title: string; aside?: React.ReactNode; intro?: string; className?: string; children: React.ReactNode }>) {
  const [open, setOpen] = useState(false);
  return (
    <div className={cn(styles.card, styles.collapsible, className)} data-open={open} data-intro-item={intro}>
      <button type="button" className={styles.cardHeader} onClick={() => setOpen(prev => !prev)} aria-expanded={open}>
        <span className={styles.cardLabel}>{title}</span>
        <span className="flex items-center gap-3">
          {aside}
          <ChevronDown aria-hidden="true" size={18} className={styles.chevron} />
        </span>
      </button>
      <div className={styles.collapsibleBody}>{children}</div>
    </div>
  );
}

function SeverityPill({ severity }: Readonly<{ severity: string }>) {
  const color = SEVERITY_COLORS[severity.toLowerCase()] ?? "#4a7a9b";
  return (
    <span
      className="inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-semibold tracking-wide uppercase"
      style={{ color, borderColor: `${color}66`, backgroundColor: `${color}1f` }}
    >
      <span className="size-1.5 rounded-full" style={{ backgroundColor: color }} />
      {severity}
    </span>
  );
}

function StatTile({ label, value, icon: Icon, accent, tone }: Readonly<{ label: string; value: number; icon: LucideIcon; accent: string; tone?: string }>) {
  return (
    <div data-intro-tile className={cn("flex items-center gap-3 rounded-xl border border-[var(--col-edge)] bg-[var(--col-deep)] px-4 py-3", INTRO_HIDDEN)}>
      <span
        className="flex size-9 shrink-0 items-center justify-center rounded-lg"
        style={{ color: accent, backgroundColor: `color-mix(in srgb, ${accent} 12%, transparent)` }}
      >
        <Icon className="size-[18px]" />
      </span>
      <div className="min-w-0">
        <p className="m-0 truncate text-[13px] tracking-wide text-white uppercase">{label}</p>
        <p className="m-0 mt-1 text-2xl leading-none font-semibold" style={{ color: tone ?? "var(--col-text)" }} data-count={value}>{value}</p>
      </div>
    </div>
  );
}

function FindingRow({ finding }: Readonly<{ finding: TopFinding }>) {
  const [open, setOpen] = useState(false);
  const color = SEVERITY_COLORS[finding.severity.toLowerCase()] ?? "#4a7a9b";
  const hasDetails = Boolean(finding.description || finding.recommendation);
  return (
    <li className="overflow-hidden rounded-lg border border-[var(--col-edge)] bg-[rgba(6,14,28,0.5)]" style={{ boxShadow: `inset 3px 0 0 ${color}` }}>
      <button
        type="button"
        onClick={() => setOpen(prev => !prev)}
        aria-expanded={open}
        disabled={!hasDetails}
        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[0.03] disabled:cursor-default disabled:hover:bg-transparent"
      >
        <SeverityPill severity={finding.severity} />
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium text-[var(--col-text)]">{finding.title}</span>
          <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--col-muted)]">
            {finding.asset_identifier && <code className="font-mono text-[var(--col-cyan)]">{finding.asset_identifier}</code>}
            <span>{sourceLabel(finding.source)}</span>
            <span>{formatDateWithYear(finding.created_at)}</span>
          </span>
        </span>
        {hasDetails && (
          <ChevronDown aria-hidden="true" className={cn("mt-0.5 size-4 shrink-0 text-[var(--col-muted)] transition-transform", open && "rotate-180")} />
        )}
      </button>
      {open && hasDetails && (
        <div className="flex flex-col gap-3 border-t border-[var(--col-edge)] px-4 py-3 text-sm">
          {finding.description && (
            <div>
              <p className="text-[11px] font-semibold tracking-wide text-[var(--col-muted)] uppercase">What this means</p>
              <p className="mt-1 text-[var(--col-text)]/90">{finding.description}</p>
            </div>
          )}
          {finding.recommendation && (
            <div className="rounded-md border border-[rgba(74,222,128,0.25)] bg-[rgba(74,222,128,0.06)] px-3 py-2">
              <p className="text-[11px] font-semibold tracking-wide text-[var(--col-success)] uppercase">How to fix</p>
              <p className="mt-1 text-[var(--col-text)]/90">{finding.recommendation}</p>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

type ReportState = "ready" | "preparing" | "failed";
const MAX_REPORT_CHECKS = 24;

function reportState(data: ExecutiveSummary | null, gaveUp: boolean): ReportState {
  const report = data?.report_status;
  if (report?.pdf_path || report?.status === "completed") return "ready";
  if (report?.status === "failed" || gaveUp) return "failed";
  return "preparing";
}

export default function ReportPage() {
  const { scan_id } = useParams<{ scan_id: string }>();
  const [data, setData] = useState<ExecutiveSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [gaveUp, setGaveUp] = useState(false);
  const [email, setEmail] = useState("");
  const [sendState, setSendState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [sentTo, setSentTo] = useState("");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let checks = 0;
    const load = () => {
      fetchScanSummary(scan_id)
        .then(result => {
          if (cancelled) return;
          setData(result);
          if (reportState(result, false) === "preparing") {
            checks += 1;
            if (checks > MAX_REPORT_CHECKS) setGaveUp(true);
            else timer = setTimeout(load, 5000);
          }
        })
        .catch((err: unknown) => {
          if (!cancelled) setError(err instanceof Error ? err.message : "Unknown error");
        });
    };
    load();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [scan_id]);

  const [intro, setIntro] = useState<IntroPhase>("pending");
  const [needle, setNeedle] = useState(0);
  const [shownScore, setShownScore] = useState<number | null>(null);
  const [gaugeScale, setGaugeScale] = useState(2);
  const rootRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const overlayGaugeRef = useRef<HTMLDivElement>(null);
  const captionRef = useRef<HTMLParagraphElement>(null);
  const overlayCardRef = useRef<HTMLDivElement>(null);
  const overlayTextColRef = useRef<HTMLDivElement>(null);
  const overlayTextInnerRef = useRef<HTMLDivElement>(null);
  const overlayNumberRef = useRef<HTMLElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);
  const orbitRef = useRef<HTMLDivElement>(null);
  const riskCardRef = useRef<HTMLDivElement>(null);
  const targetGaugeRef = useRef<HTMLDivElement>(null);
  const targetTextRef = useRef<HTMLDivElement>(null);
  const needleRef = useRef(0);
  const timelineRef = useRef<Timeline | null>(null);

  useEffect(() => {
    let seen = false;
    try { seen = localStorage.getItem(introSeenKey(scan_id)) === "1"; } catch {}
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setGaugeScale(Math.min(2.2, (window.innerWidth * 0.8) / GAUGE_WIDTH));
    setIntro(seen || reduce ? "off" : "loading");
  }, [scan_id]);

  const markSeen = () => {
    try { localStorage.setItem(introSeenKey(scan_id), "1"); } catch {}
  };

  useEffect(() => {
    if (intro !== "loading" && intro !== "playing") return;
    const html = document.documentElement;
    const previous = html.style.overflow;
    html.style.overflow = "hidden";
    const skip = () => {
      markSeen();
      const tl = timelineRef.current;
      if (tl) {
        tl.seek(tl.duration);
        tl.complete();
      } else setIntro("off");
    };
    const events = ["pointerdown", "keydown", "wheel", "touchstart"] as const;
    events.forEach(name => window.addEventListener(name, skip, { passive: true }));
    return () => {
      html.style.overflow = previous;
      events.forEach(name => window.removeEventListener(name, skip));
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intro]);

  useEffect(() => {
    if (intro !== "loading") return;
    let sweep: JSAnimation | null = null;
    let cancelled = false;
    import("animejs").then(({ animate }) => {
      if (cancelled) return;
      const value = { v: 8 };
      sweep = animate(value, {
        v: 58,
        duration: 1100 * INTRO_SPEED,
        ease: "inOutSine",
        alternate: true,
        loop: true,
        onUpdate: () => { needleRef.current = value.v; setNeedle(value.v); },
      });
    });
    return () => { cancelled = true; sweep?.cancel(); };
  }, [intro]);

  useEffect(() => {
    if (intro === "loading" && data) setIntro("playing");
  }, [intro, data]);

  useLayoutEffect(() => {
    if (intro !== "playing") return;
    window.scrollTo(0, 0);
    rootRef.current?.querySelectorAll<HTMLElement>("[data-count]").forEach(el => { el.textContent = "0"; });
  }, [intro]);

  useEffect(() => {
    if (intro !== "playing" || !data) return;
    let cancelled = false;
    const root = rootRef.current;
    const finish = () => {
      root?.querySelectorAll<HTMLElement>("[data-count]").forEach(el => { el.textContent = el.dataset.count ?? el.textContent; });
      if (targetGaugeRef.current) targetGaugeRef.current.style.visibility = "visible";
      if (targetTextRef.current) targetTextRef.current.style.clipPath = "none";
      timelineRef.current = null;
      markSeen();
      setIntro("done");
    };

    import("animejs").then(({ createTimeline, stagger }) => {
      const gauge = overlayGaugeRef.current;
      const target = targetGaugeRef.current;
      if (cancelled || !root || !gauge || !target || !data) return;
      const score = riskFor(data.risk_snapshot).score;

      const card = gauge;
      const textCol = overlayTextColRef.current;
      const textInner = overlayTextInnerRef.current;
      const realText = targetTextRef.current;
      const realCard = riskCardRef.current;
      if (!textCol || !textInner || !realText || !realCard) return;

      const phone = window.matchMedia("(max-width: 640px)").matches;
      const gaugeBox = target.getBoundingClientRect();
      const textBox = realText.getBoundingClientRect();
      const cs = getComputedStyle(card);
      const padX = parseFloat(cs.paddingLeft) + parseFloat(cs.borderLeftWidth);
      const padY = parseFloat(cs.paddingTop) + parseFloat(cs.borderTopWidth);
      const gap = phone ? 12 : 24;
      textInner.style.width = `${textBox.width}px`;
      const verdictLine = realText.lastElementChild as HTMLElement | null;
      if (verdictLine) verdictLine.style.clipPath = "inset(0% 100% 0% 0%)";
      const textWidthOf = (el: Element | null) => {
        if (!el) return 0;
        const range = document.createRange();
        range.selectNodeContents(el);
        return range.getBoundingClientRect().width;
      };
      const headingW = Math.ceil(Math.max(textWidthOf(realText.children[0] ?? null), textWidthOf(realText.children[1] ?? null))) + 4;
      const extendW = Math.min(textBox.width, headingW);
      const fullW = phone ? Math.max(gaugeBox.width, textBox.width) + padX * 2 : padX * 2 + gaugeBox.width + gap + extendW;
      const fullH = phone ? padY * 2 + gaugeBox.height + gap + textBox.height : padY * 2 + Math.max(gaugeBox.height, textBox.height);
      const fitScale = Math.min(gaugeScale, (window.innerWidth * 0.9) / fullW, (window.innerHeight * 0.8) / fullH);
      const gaugeOffsetX = phone ? 0 : -fullW / 2 + padX + gaugeBox.width / 2;
      const gaugeOffsetY = phone ? -fullH / 2 + padY + gaugeBox.height / 2 : 0;
      const dx = gaugeBox.left + gaugeBox.width / 2 - gaugeOffsetX - window.innerWidth / 2;
      const dy = gaugeBox.top + gaugeBox.height / 2 - gaugeOffsetY - window.innerHeight / 2;

      const needleValue = { v: needleRef.current };
      let lastTick = 0;
      let lastShown = 0;
      let lastValue = needleValue.v;
      const numberValue = { v: 0 };
      const color = riskColorFor(score);
      const t = (ms: number) => ms * INTRO_SPEED;
      const countUp = (tl: Timeline, el: HTMLElement, at: number, duration: number, ease = "outCubic") => {
        const end = Number(el.dataset.count ?? 0);
        const value = { v: 0 };
        tl.add(value, { v: end, duration, ease, onUpdate: () => { el.textContent = String(Math.round(value.v)); } }, at);
      };
      const numberGlow = (tl: Timeline, at: number) => {
        const el = overlayNumberRef.current;
        if (!el) return;
        tl.add(el, { textShadow: ["0 0 0px rgba(0,0,0,0)", `0 0 18px ${color}`], duration: t(400), ease: "outQuad" }, at);
      };

      const tl = createTimeline({ onComplete: finish });
      tl.add(needleValue, { v: 0, duration: t(400), ease: "outQuad", onUpdate: () => setNeedle(needleValue.v) }, 0)
        .call(() => setShownScore(0), 0);

      const sweepAt = t(400) + HOLD_AT_ZERO_MS;
      tl.add(glowRef.current ?? {}, { opacity: [0, 1], scale: [0.85, 1], duration: HOLD_AT_ZERO_MS, ease: "inOutSine" }, t(400))
        .add(orbitRef.current ?? {}, { opacity: [0, 0.7], duration: t(600), ease: "outQuad" }, sweepAt)
        .add(needleValue, { v: score, duration: t(1300), ease: "outBack(1.6)", onUpdate: () => {
          setNeedle(needleValue.v);
          const now = performance.now();
          const speed = lastTick ? Math.abs(needleValue.v - lastValue) / Math.max(1, now - lastTick) : 0;
          lastTick = now;
          lastValue = needleValue.v;
          const surge = Math.min(1, speed * 6);
          const value = Math.max(0, Math.min(100, needleValue.v)) / 100;
          const glow = glowRef.current;
          if (glow) {
            glow.style.boxShadow = `0 0 ${80 + surge * 50 + value * 20}px ${16 + surge * 14 + value * 8}px ${riskColorFor(needleValue.v)}${surge > 0.3 ? "99" : "80"}`;
          }
        } }, sweepAt)
        .add(numberValue, { v: score, duration: t(1300), ease: "outCubic", onUpdate: () => {
          const whole = Math.round(numberValue.v);
          if (whole === lastShown) return;
          lastShown = whole;
          setShownScore(whole);
          overlayNumberRef.current?.animate([{ transform: "scale(1.25)" }, { transform: "scale(1)" }], { duration: 260, easing: "ease-out" });
        } }, sweepAt);

      const holdAt = sweepAt + t(1300);
      numberGlow(tl, holdAt);

      const extendAt = holdAt + HOLD_AT_SCORE_MS;
      tl.add(captionRef.current ?? {}, { opacity: 0, duration: t(300) }, extendAt)
        .add(textCol, phone
          ? { height: [0, textBox.height], marginTop: [0, gap], duration: t(700), ease: "inOutCubic" }
          : { width: [0, extendW], marginLeft: [0, gap], duration: t(700), ease: "inOutCubic" }, extendAt)
        .add(card, { scale: [gaugeScale, fitScale], duration: t(700), ease: "inOutCubic" }, extendAt);

      const moveAt = extendAt + t(700) + HOLD_AFTER_REVEAL_MS;
      tl.add(card, { translateX: [0, dx], translateY: [0, dy], scale: [fitScale, 1], duration: t(800), ease: "inOutCubic" }, moveAt)
        .add(backdropRef.current ?? {}, { opacity: 0, duration: t(800), ease: "inOutQuad" }, moveAt)
        .add(overlayCardRef.current ?? {}, { opacity: 0, duration: t(400), ease: "inQuad" }, moveAt + t(400))
        .add(glowRef.current ?? {}, { opacity: 0, duration: t(500), ease: "inQuad" }, moveAt)
        .add(orbitRef.current ?? {}, { opacity: 0, duration: t(500), ease: "inQuad" }, moveAt)
        .add(realCard, { opacity: [0, 1], duration: t(400) }, moveAt + t(400))
        .call(() => {
          target.style.visibility = "visible";
          realText.style.clipPath = "none";
          if (overlayRef.current) overlayRef.current.style.display = "none";
        }, moveAt + t(800))
        .add(verdictLine ?? {}, {
          clipPath: ["inset(0% 100% 0% 0%)", "inset(0% 0% 0% 0%)"],
          duration: t(700),
          ease: "inOutQuad",
        }, moveAt + t(850));
      const statsAt = moveAt + t(1500);

      let stage3End = statsAt + t(100);
      const assets = root.querySelector<HTMLElement>('[data-intro-item="assets"]');
      if (assets) {
        tl.add(assets, { opacity: [0, 1], translateY: [12, 0], duration: t(400), ease: "outQuad" }, statsAt);
        let rowStart = statsAt + t(200);
        assets.querySelectorAll<HTMLElement>("[data-intro-bar]").forEach(bar => {
          const count = bar.closest("li")?.querySelector<HTMLElement>("[data-count]");
          const end = Number(count?.dataset.count ?? 0);
          if (end <= 0) return;
          const units = Math.min(end, MAX_STEPPED_COUNT);
          const progress = { v: 0 };
          let shown = 0;
          tl.add(progress, {
            v: 1,
            duration: (units + 1) * STEP_MS,
            ease: constantThenSettle(units),
            onUpdate: () => {
              bar.style.transform = `scaleX(${progress.v})`;
              const whole = Math.min(end, Math.floor(progress.v * end + 1e-6));
              if (whole === shown || !count) return;
              shown = whole;
              count.textContent = String(whole);
              count.animate([{ transform: "scale(1.25)" }, { transform: "scale(1)" }], { duration: 260, easing: "ease-out" });
              bar.animate([{ filter: "brightness(1.6)" }, { filter: "brightness(1)" }], { duration: 220, easing: "ease-out" });
            },
          }, rowStart);
          rowStart += (units + 1) * STEP_MS;
          stage3End = Math.max(stage3End, rowStart);
        });
      }
      const tiles = root.querySelectorAll<HTMLElement>("[data-intro-tile]");
      tl.add(tiles, { opacity: [0, 1], translateY: [12, 0], duration: t(400), ease: "outQuad", delay: stagger(t(200)) }, statsAt + t(100));
      tiles.forEach((tile, i) => {
        const el = tile.querySelector<HTMLElement>("[data-count]");
        if (!el) return;
        const at = statsAt + t(100) + i * t(200);
        countUp(tl, el, at, t(900));
        stage3End = Math.max(stage3End, at + t(900));
      });

      tl.add(root.querySelectorAll('[data-intro-item="rest"]'), { opacity: [0, 1], translateY: [16, 0], duration: t(500), ease: "outQuad", delay: stagger(t(120)) }, stage3End + t(150));

      timelineRef.current = tl;
    });

    return () => {
      cancelled = true;
      timelineRef.current?.cancel();
      timelineRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intro, data === null]);

  const introOverlay = (intro === "loading" || intro === "playing") && (
    <div ref={overlayRef} aria-hidden="true" className="fixed inset-0 z-[60]">
      <div ref={backdropRef} className="absolute inset-0 bg-[#050914]/95 backdrop-blur-sm" />
      <div className="absolute inset-0 flex items-center justify-center">
        <div
          ref={overlayGaugeRef}
          className={cn(styles.card, "relative flex items-center max-sm:flex-col max-sm:text-center")}
          style={{ transform: `scale(${gaugeScale})`, background: "transparent", borderColor: "transparent" }}
        >
          <div
            ref={glowRef}
            className="absolute -inset-px -z-20 rounded-[14px] opacity-0 transition-shadow duration-150"
            style={{ boxShadow: `0 0 80px 16px ${riskColorFor(needle)}80` }}
          />
          <div aria-hidden="true" className="absolute -inset-3 -z-20 overflow-hidden rounded-[22px] blur-xl">
            <div
              ref={orbitRef}
              className="absolute top-1/2 left-1/2 aspect-square w-[160%] -translate-x-1/2 -translate-y-1/2 animate-[spin_5s_linear_infinite] opacity-0"
              style={{ background: `conic-gradient(from 0deg, transparent 0deg 220deg, ${riskColorFor(needle)} 290deg, transparent 340deg)` }}
            />
          </div>
          <div
            ref={overlayCardRef}
            className="absolute -inset-px -z-10 rounded-[14px] border border-[var(--col-edge)] bg-[var(--col-deep)] shadow-[0_20px_60px_-20px_rgba(0,0,0,0.8)]"
          />
          <div className="shrink-0">
            <RiskGauge score={needle} />
            <p className="-mt-1 text-center">
              <strong ref={overlayNumberRef} className="inline-block text-3xl leading-none" style={{ color: riskColorFor(shownScore ?? 0) }}>{shownScore ?? "--"}</strong>
              <span className="text-xs text-[var(--col-muted)]">/100</span>
            </p>
          </div>
          <div ref={overlayTextColRef} className="w-0 overflow-hidden max-sm:h-0 max-sm:w-auto">
            {data && (
              <div ref={overlayTextInnerRef} className="min-w-0">
                <p className="text-xs tracking-wide text-[var(--col-muted)] uppercase">Overall risk</p>
                <p className="mt-1 text-2xl font-semibold" style={{ color: riskFor(data.risk_snapshot).color }}>
                  {riskFor(data.risk_snapshot).level} risk
                </p>
                <p className="invisible mt-2 text-sm text-[var(--col-text)]">{verdict(data.risk_snapshot)}</p>
              </div>
            )}
          </div>
        </div>
      </div>
      <p ref={captionRef} className="absolute inset-x-0 top-[calc(50%+240px)] text-center max-sm:top-[calc(50%+170px)] text-sm tracking-wide text-[var(--col-muted)] uppercase">
        {data ? `Calculating risk for ${data.scan_summary.domain}...` : "Analysing your scan..."}
      </p>
      <p className="absolute inset-x-0 bottom-8 text-center text-xs text-[var(--col-muted)]/70 [animation:intro-hint-in_0.6s_ease-out_1s_both]">
        Click or press any key to skip
      </p>
    </div>
  );

  if (!data) {
    return (
      <div className={styles.reportPage}>
        <NavBar />
        {introOverlay}
        <div className={styles.stateWrap}>
          {error ? (
            <>
              <p className={styles.stateText}>FAILED TO LOAD REPORT</p>
              <p className={styles.errorText}>{error}</p>
            </>
          ) : (
            <p className={styles.stateText}>LOADING REPORT...</p>
          )}
        </div>
      </div>
    );
  }

  const { scan_summary, risk_snapshot, top_findings, asset_impact } = data;
  const risk = riskFor(risk_snapshot);
  const state = reportState(data, gaveUp);
  const pdfUrl = getReportPdfUrl(scan_id);
  const took = duration(scan_summary.started_at, scan_summary.completed_at);

  const maxAssetCount = Math.max(1, ...asset_impact.asset_type_breakdown.map(row => row.total_assets));

  const handleSendReport = async (e: React.FormEvent) => {
    e.preventDefault();
    const target = email.trim();
    if (!target) return;
    setSendState("sending");
    try {
      await sendReportEmail(scan_id, target);
      setSentTo(target);
      setSendState("sent");
      setEmail("");
    } catch (err) {
      console.error(err);
      setSendState("error");
    }
  };

  const downloadButton = (className?: string) => state === "ready" ? (
    <a
      href={pdfUrl}
      download
      className={cn("inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-[var(--col-cyan)] px-5 text-sm font-semibold text-[#04121f] no-underline transition-colors hover:bg-[var(--col-cyan)]/85", className)}
    >
      <Download className="size-4" />
      Download PDF
    </a>
  ) : (
    <span
      aria-disabled="true"
      className={cn(
        "inline-flex h-11 cursor-not-allowed items-center justify-center gap-2 rounded-lg border px-5 text-sm font-semibold",
        state === "failed" ? "border-[rgba(255,95,78,0.4)] text-[var(--col-alert)]" : "border-[var(--col-edge)] text-[var(--col-muted)]",
        className
      )}
    >
      {state === "failed" ? <AlertTriangle className="size-4" /> : <Loader2 className="size-4 animate-spin" />}
      {state === "failed" ? "PDF unavailable" : "Preparing PDF..."}
    </span>
  );

  return (
    <div ref={rootRef} className={cn(styles.reportPage, "group/report max-sm:pb-20")} data-intro={intro === "playing" ? "playing" : undefined}>
      <NavBar />
      {introOverlay}
      {intro === "done" && (
        <p role="status" className="sr-only">Risk score {risk.score} out of 100, {risk.level} risk. {verdict(risk_snapshot)}</p>
      )}

      <section className={styles.hero}>
        <div className={styles.heroTextWrap}>
          <h1>REPORT SUMMARY</h1>
          <p className={styles.heroDomain}>{scan_summary.domain.toUpperCase()}</p>
          <p className="mt-1.5 text-sm text-[#334155]">
            {scan_summary.completed_at ? `Completed ${formatDateTime(scan_summary.completed_at)}` : `Started ${formatDateTime(scan_summary.created_at)}`}
            {took && ` · took ${took}`}
          </p>
        </div>
        <div className={styles.waterline} aria-hidden="true">
          <svg
            viewBox="0 0 1440 200"
            xmlns="http://www.w3.org/2000/svg"
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
            preserveAspectRatio="none"
          >
            <path d="M0,40 Q180,80 360,40 T720,40 T1080,40 T1440,40 V200 H0 Z" fill="rgba(43,180,220,0.35)" />
            <path d="M0,90 Q200,130 400,90 T800,90 T1200,90 T1440,90 V200 H0 Z" fill="rgba(15,37,75,0.9)" />
            <path d="M0,150 Q220,178 440,150 T880,150 T1320,150 T1440,150 V200 H0 Z" fill="#091628" />
          </svg>
        </div>
      </section>

      <div className={styles.content}>
        <div ref={riskCardRef} className={cn(styles.card, "flex items-center gap-6 max-sm:flex-col max-sm:gap-3 max-sm:text-center", INTRO_HIDDEN)}>
          <div ref={targetGaugeRef} className="shrink-0 group-data-[intro=playing]/report:invisible">
            <RiskGauge score={risk.score} />
            <p className="-mt-1 text-center">
              <strong className="text-3xl leading-none" style={{ color: risk.color }}>{risk.score}</strong>
              <span className="text-xs text-[var(--col-muted)]">/100</span>
            </p>
          </div>
          <div ref={targetTextRef} className="min-w-0 group-data-[intro=playing]/report:[clip-path:inset(0_100%_0_0)]">
            <p className="text-xs tracking-wide text-[var(--col-muted)] uppercase">Overall risk</p>
            <p className="mt-1 text-2xl font-semibold" style={{ color: risk.color }}>{risk.level} risk</p>
            <p className="mt-2 text-sm text-[var(--col-text)]">{verdict(risk_snapshot)}</p>
          </div>
        </div>

        <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] items-stretch gap-3.5 max-[900px]:grid-cols-1 max-sm:gap-2">
          <CollapsibleCard title="EXPOSED ASSETS" intro="assets" className={INTRO_HIDDEN}>
            {asset_impact.asset_type_breakdown.length === 0 ? (
              <p className={styles.emptyText}>No assets recorded.</p>
            ) : (
              <div className="flex flex-col gap-4">
                <ul className="flex flex-col gap-2.5">
                  {asset_impact.asset_type_breakdown.map(row => {
                    const color = assetTypeColor(row.asset_type);
                    return (
                    <li key={row.asset_type} className="flex flex-col gap-1">
                      <span className="flex items-center justify-between text-sm">
                        <span
                          className="rounded border px-1.5 py-0.5 text-[11px] tracking-wide uppercase"
                          style={{ color, borderColor: `color-mix(in srgb, ${color} 35%, transparent)` }}
                        >
                          {formatEnumLabel(row.asset_type)}
                        </span>
                        <span className="inline-block font-semibold" style={{ color }} data-count={row.total_assets}>{row.total_assets}</span>
                      </span>
                      <span className="relative h-1.5 overflow-hidden rounded-full bg-white/5">
                        <span aria-hidden="true" className="absolute inset-y-0 w-0.5 -translate-x-full bg-white/25" style={{ left: `${(row.total_assets / maxAssetCount) * 100}%` }} />
                        <span data-intro-bar className="relative block h-full origin-left rounded-full opacity-75 group-data-[intro=playing]/report:[transform:scaleX(0)] group-data-[intro=playing]/report:will-change-transform" style={{ width: `${(row.total_assets / maxAssetCount) * 100}%`, backgroundColor: color }} />
                      </span>
                    </li>
                    );
                  })}
                </ul>
                {asset_impact.top_affected_assets.length > 0 && (
                  <div className="border-t border-[var(--col-edge)] pt-3">
                    <p className="mb-2 text-[11px] font-semibold tracking-wide text-[var(--col-muted)] uppercase">Most affected</p>
                    <ul className="flex flex-col gap-1.5">
                      {asset_impact.top_affected_assets.slice(0, 5).map(asset => (
                        <li key={asset.identifier} className="flex items-center gap-2 text-sm">
                          <span
                            className="size-2 shrink-0 rounded-full"
                            title={`Worst: ${asset.highest_severity}`}
                            style={{ backgroundColor: SEVERITY_COLORS[asset.highest_severity.toLowerCase()] ?? "#4a7a9b" }}
                          />
                          <code className="min-w-0 flex-1 truncate font-mono text-xs text-[var(--col-text)]">{asset.identifier}</code>
                          <span className="shrink-0 text-xs text-[var(--col-muted)]">
                            {asset.finding_count} finding{asset.finding_count === 1 ? "" : "s"}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </CollapsibleCard>
        <div className="grid auto-rows-fr grid-cols-2 gap-3.5 max-[900px]:order-first max-sm:gap-2">
          <StatTile label="Findings" value={risk_snapshot.total_findings} icon={Bug} accent="#ff5f4e" />
          <StatTile
            label="Critical / High"
            icon={ShieldAlert}
            accent={SEVERITY_COLORS.high}
            value={risk_snapshot.critical_count + risk_snapshot.high_count}
            tone={risk_snapshot.critical_count + risk_snapshot.high_count > 0 ? SEVERITY_COLORS.high : undefined}
          />
          <StatTile label="Assets scanned" value={asset_impact.total_assets_scanned} icon={Globe} accent="#2bd8f5" />
          <StatTile label="Assets affected" value={asset_impact.affected_assets_count} icon={Target} accent="#c084fc" tone={asset_impact.affected_assets_count > 0 ? "var(--col-cyan)" : undefined} />
        </div>
        </div>

        <CollapsibleCard title="TOP FINDINGS" intro="rest" className={INTRO_HIDDEN} aside={<span className="text-xs text-[var(--col-muted)]">{top_findings.length}</span>}>
          {top_findings.length === 0 ? (
            <p className={styles.emptyText}>No findings recorded.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {top_findings.map(f => <FindingRow key={f.id} finding={f} />)}
            </ul>
          )}
        </CollapsibleCard>

        <div id="get-report" data-intro-item="rest" className={cn(styles.card, "scroll-mt-24", INTRO_HIDDEN)}>
          <span className={styles.cardLabel}>GET THE FULL REPORT</span>
          <p className="-mt-2 mb-4 text-sm text-[var(--col-muted)]">
            The PDF includes every finding with details and recommended fixes.
          </p>
          <div className="flex items-start gap-3 max-sm:flex-col max-sm:items-stretch">
            {downloadButton("max-sm:w-full")}
            <form onSubmit={handleSendReport} className="flex min-w-0 flex-1 flex-col gap-1.5">
              <div className="flex h-11 overflow-hidden rounded-lg border border-[var(--col-edge-hot)] focus-within:border-[var(--col-cyan)]">
                <span className="flex items-center pl-3 text-[var(--col-muted)]"><Mail className="size-4" /></span>
                <input
                  type="email"
                  required
                  placeholder="your@email.com"
                  aria-label="Email address"
                  value={email}
                  onChange={e => { setEmail(e.target.value); if (sendState !== "sending") setSendState("idle"); }}
                  className="min-w-0 flex-1 bg-transparent px-3 text-sm text-[var(--col-text)] outline-none placeholder:text-[var(--col-muted)] max-sm:text-base"
                />
                <button
                  type="submit"
                  disabled={!email.trim() || sendState === "sending"}
                  className="shrink-0 border-l border-[var(--col-edge-hot)] px-4 text-sm font-semibold text-[var(--col-cyan)] transition-colors hover:bg-[var(--col-cyan)]/10 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {sendState === "sending" ? "Sending..." : "Email it"}
                </button>
              </div>
              {sendState === "sent" && (
                <p className="flex items-center gap-1.5 text-xs text-[var(--col-success)]"><Check className="size-3.5" /> Sent to {sentTo}</p>
              )}
              {sendState === "error" && (
                <p className="flex items-center gap-1.5 text-xs text-[var(--col-alert)]"><AlertTriangle className="size-3.5" /> Couldn&apos;t send the report. Please try again.</p>
              )}
            </form>
          </div>
        </div>

        <div data-intro-item="rest" className="flex items-center gap-5 rounded-[14px] border border-[rgba(43,216,245,0.3)] group-data-[intro=playing]/report:opacity-0 bg-gradient-to-br from-[rgba(43,216,245,0.1)] to-transparent px-8 py-6 max-sm:flex-col max-sm:items-stretch max-sm:px-5">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-[var(--col-cyan)]/15 text-[var(--col-cyan)] max-sm:hidden">
            <Radar className="size-5" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold text-[var(--col-text)]">Want a deeper look?</p>
            <p className="mt-1 text-sm text-[var(--col-muted)]">
              This was a passive scan of public information. Verify you own {scan_summary.domain} to run an active scan of your services, ports and vulnerabilities.
            </p>
          </div>
          <div className="flex shrink-0 flex-col gap-2">
            <Link href="/register" className="inline-flex h-10 items-center justify-center gap-1.5 rounded-lg bg-[var(--col-cyan)] px-4 text-sm font-semibold text-[#04121f] no-underline hover:bg-[var(--col-cyan)]/85">
              <ShieldCheck className="size-4" />
              Get started
              <ArrowRight className="size-4" />
            </Link>
            <Link href="/api/auth/login" className="text-center text-xs text-[var(--col-muted)] no-underline hover:text-[var(--col-cyan)]">
              I already have an account
            </Link>
          </div>
        </div>
      </div>

      <div data-intro-item="rest" className="fixed inset-x-0 bottom-0 z-40 hidden gap-2 group-data-[intro=playing]/report:opacity-0 border-t border-[var(--col-edge)] bg-[#050914]/95 px-4 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur max-sm:flex">
        {downloadButton("flex-1")}
        <a href="#get-report" className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-lg border border-[var(--col-edge-hot)] text-sm font-semibold text-[var(--col-cyan)] no-underline">
          <Mail className="size-4" />
          Email
        </a>
      </div>
    </div>
  );
}