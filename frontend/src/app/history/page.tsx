"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import NavBar from "@/components/NavBar";
import { fetchScanHistory, getReportPdfUrl, SEVERITY_COLORS, formatDate } from "@/lib/scanService";
import type { ScanHistoryItem } from "@/lib/scanService";
import Image from "next/image";
import submarineImage from "@/app/images/images/submarine.png";
import styles from "./history.module.css";


function SeverityDots({ count, color }: { count: number; color: string }) {
  return Array.from({ length: Math.min(count, 8) }).map((_, i) => (
    <span key={`${color}-${i}`} className={styles.dot} style={{ backgroundColor: color }} />
  ));
}

export default function HistoryPage() {
  const router = useRouter();
  const [scans, setScans] = useState<ScanHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [emailSent, setEmailSent] = useState<Record<string, boolean>>({});
  const [modal, setModal] = useState<ScanHistoryItem | null>(null);
  const [dragPos, setDragPos] = useState<{ x: number; y: number } | null>(null);
  const dragOffset = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const isDragging = useRef(false);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      setDragPos({ x: e.clientX - dragOffset.current.x, y: e.clientY - dragOffset.current.y });
    };
    const onUp = () => { isDragging.current = false; };
    globalThis.addEventListener("mousemove", onMove);
    globalThis.addEventListener("mouseup", onUp);
    return () => { globalThis.removeEventListener("mousemove", onMove); globalThis.removeEventListener("mouseup", onUp); };
  }, []);

  const startDrag = (e: React.MouseEvent<HTMLElement>) => {
    const rect = (e.currentTarget.closest("[data-modal]") as HTMLElement).getBoundingClientRect();
    dragOffset.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    isDragging.current = true;
    e.preventDefault();
  };

  useEffect(() => {
    fetchScanHistory()
      .then(setScans)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Unknown error"))
      .finally(() => setLoading(false));
  }, []);

  const openModal = (scan: ScanHistoryItem, e: React.MouseEvent) => {
    e.stopPropagation();
    setModal(scan);
  };

  const closeModal = () => { setModal(null); setDragPos(null); };

  const handleSendEmail = (scanId: string) => {
    setEmailSent(prev => ({ ...prev, [scanId]: true }));
    closeModal();
  };

  return (
    <div
      className={styles.historyPage}
      role="button"
      tabIndex={0}
      onClick={modal ? closeModal : undefined}
      onKeyDown={modal ? (e) => e.key === "Escape" && closeModal() : undefined}
    >
      <NavBar />

      {/* Hero */}
      <section className={styles.hero}>
        <div className={styles.heroTextWrap}>
          <h1>SCAN HISTORY</h1>
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
          <Image
            src={submarineImage}
            alt="Submarine illustration"
            width={200}
            height={125}
            className={styles.submarine}
            priority
          />
        </div>
      </section>

      <div className={styles.content}>
        {(() => {
          if (loading) return <div className={styles.stateWrap}><p className={styles.stateText}>LOADING HISTORY...</p></div>;
          if (error) return <div className={styles.stateWrap}><p className={styles.stateText}>{error}</p></div>;
          if (scans.length === 0) return <div className={styles.stateWrap}><p className={styles.stateText}>NO SCANS YET</p></div>;
          return (
          <div className={styles.card}>
            <table className={styles.table}>
              <colgroup>
                <col style={{ width: "38%" }} />
                <col style={{ width: "40%" }} />
                <col style={{ width: "22%" }} />
              </colgroup>
              <thead>
                <tr>
                  <th>DOMAIN</th>
                  <th>FINDINGS</th>
                  <th>DATE</th>
                </tr>
              </thead>
              <tbody>
                {scans.map(scan => (
                  <tr
                    key={scan.id}
                    className={styles.clickableRow}
                    onClick={e => openModal(scan, e)}
                  >
                    <td className={styles.domainCell}>{scan.domain}</td>
                    <td>
                      <div className={styles.findingsCell}>
                        <span className={styles.total}>{scan.total_findings}</span>
                        <div className={styles.severityDots}>
                          <SeverityDots count={scan.critical_count} color={SEVERITY_COLORS.critical} />
                          <SeverityDots count={scan.high_count}     color={SEVERITY_COLORS.high} />
                          <SeverityDots count={scan.medium_count}   color={SEVERITY_COLORS.medium} />
                          <SeverityDots count={scan.low_count}      color={SEVERITY_COLORS.low} />
                        </div>
                      </div>
                    </td>
                    <td className={styles.dateCell}>{formatDate(scan.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          );
        })()}
      </div>

      {/* Row action modal */}
      {modal && (
        <>
          <div
            className={styles.modalBackdrop}
            role="button"
            tabIndex={0}
            onClick={closeModal}
            onKeyDown={(e) => e.key === "Escape" && closeModal()}
          />
          <div
            className={styles.modal}
            data-modal
            onClick={e => e.stopPropagation()}
            style={dragPos ? { left: dragPos.x, top: dragPos.y, transform: "none" } : undefined}
          >
            <div
              className={styles.modalDomain}
              role="button"
              tabIndex={0}
              onMouseDown={startDrag}
            >
              {modal.domain}
            </div>

            <button
              className={`${styles.modalBtn} ${styles.modalBtnReport}`}
              onClick={() => { closeModal(); router.push(`/report/${modal.id}`); }}
            >
            VIEW REPORT
            </button>
            <a
              href={getReportPdfUrl(modal.id)}
              target="_blank"
              rel="noopener noreferrer"
              className={`${styles.modalBtn} ${styles.modalBtnDownload}`}
              onClick={closeModal}
            >
              ↓ DOWNLOAD PDF
            </a>
            <button
              className={`${styles.modalBtn} ${styles.modalBtnSend}`}
              disabled={!!emailSent[modal.id]}
              onClick={() => handleSendEmail(modal.id)}
            >
              {emailSent[modal.id] ? "EMAIL SENT" : "SEND EMAIL"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
