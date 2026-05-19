"use client";

import { useEffect } from "react";
import type { CSSProperties } from "react";
import Image from "next/image";
import submarineImage from "@/app/images/images/submarine.png";
import styles from "./SonarSection.module.css";

const DOT_GRID_COLS = 41;
const DOT_GRID_ROWS = 41;
const DOT_CENTER_X = (DOT_GRID_COLS - 1) / 2;
const DOT_CENTER_Y = (DOT_GRID_ROWS - 1) / 2;
const DOT_MAX_RADIUS = Math.min(DOT_CENTER_X, DOT_CENTER_Y);

// red dots in the sonar scan graphic
const HOT_DOTS: ReadonlySet<number> = new Set(
  ([
    [30, 12], [10, 24], [33, 28], [15, 8], [25, 35], [7, 18], [36, 18],
  ] as [number, number][])
    .filter(([col, row]) => {
      const dx = col - DOT_CENTER_X;
      const dy = row - DOT_CENTER_Y;
      return Math.sqrt(dx * dx + dy * dy) <= DOT_MAX_RADIUS;
    })
    .map(([col, row]) => row * DOT_GRID_COLS + col),
);

export default function SonarSection() {
  useEffect(() => {
    let disposed = false;

    const run = async () => {
      const animeModule = await import("animejs");
      const createTimeline = animeModule.createTimeline;
      const animate = animeModule.animate;
      const stagger = animeModule.stagger;
      if (!createTimeline || !animate || !stagger || disposed) return;

      const options = {
        grid: [DOT_GRID_COLS, DOT_GRID_ROWS] as [number, number],
        from: "center" as const,
      };
      
      const LOOP_MS = 3240;

      createTimeline({ loop: true })
        .add(
          ".sonarDot",
          {
            scale: [0.5, 1.8, 0.7],
            opacity: [0.25, 0.6, 0.3],
            ease: "inOutSine",
            duration: 920,
          },
          stagger(95, options),
        )
        .add(".sonarDot", {
          scale: 0.5,
          opacity: 0.25,
          duration: 420,
          ease: "outQuad",
        });

      // Neon glow fires when the wave front reaches each hot dot
      const readDelay = (el: Element) =>
        parseInt((el as HTMLElement).dataset.waveDelay ?? "0", 10);

      animate(".sonarHotDot", {
        boxShadow: [
          "0 0 4px 1px rgba(255, 30, 30, 0.35)",
          "0 0 28px 12px rgba(255, 10, 10, 1)",
          "0 0 4px 1px rgba(255, 30, 30, 0.35)",
        ],
        ease: "inOutSine",
        duration: 920,
        loop: true,
        delay: readDelay,
        endDelay: (el: Element) => Math.max(0, LOOP_MS - 920 - readDelay(el)),
      });
    };

    run();
    return () => {
      disposed = true;
    };
  }, []);

  return (
    <section id="about" className={styles.sonarSection}>
      <div className={styles.sonarPanel} aria-hidden="true">
        <div className={styles.sonarStage}>
          <div className={styles.sonarDotField}>
            {Array.from({ length: DOT_GRID_COLS * DOT_GRID_ROWS }).map((_, index) => {
              const row = Math.floor(index / DOT_GRID_COLS);
              const col = index % DOT_GRID_COLS;
              const dx = col - DOT_CENTER_X;
              const dy = row - DOT_CENTER_Y;
              const dist = Math.sqrt(dx * dx + dy * dy);
              const inCircle = dist <= DOT_MAX_RADIUS;
              const isHot = HOT_DOTS.has(index);

              return (
                <span
                  key={index}
                  className={`sonarDot ${styles.sonarDot}${isHot ? ` ${styles.sonarHotDot}` : ""}`}
                  data-wave-delay={isHot ? String(Math.round(dist) * 95) : undefined}
                  style={
                    {
                      "--dot-alpha": inCircle ? "0.25" : "0.04",
                    } as CSSProperties
                  }
                />
              );
            })}
          </div>

          <div className={styles.sonarSubmarineWrap}>
            <Image
              src={submarineImage}
              alt=""
              width={308}
              height={193}
              className={styles.sonarSubmarine}
            />
          </div>
        </div>
      </div>

      <div className={styles.sonarCopy}>
        <h2>WHAT IS A CTEM SCAN?</h2>
        <p>
          THE SCAN STARTS WITH YOUR DOMAIN AND FOLLOWS PUBLIC SIGNALS:
          SUBDOMAINS, DNS RECORDS, CERTIFICATES, EXPOSED SERVICES, METADATA, AND
          OTHER OSINT CLUES ATTACKERS CAN ALREADY INSPECT.
        </p>
        <p>
          PENFLOW GROUPS THOSE SIGNALS INTO ASSETS AND FINDINGS, HIGHLIGHTS
          SUSPICIOUS EXPOSURE, AND PREPARES THE EVIDENCE INTO A COMPREHENSIVE REPORT.
        </p>
      </div>
    </section>
  );
}
