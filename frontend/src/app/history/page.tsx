"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import NavBar from "@/components/NavBar";
import { fetchScanHistory, getReportPdfUrl, formatDate } from "@/lib/scanService";
import type { ScanHistoryItem } from "@/lib/scanService";
import Image from "next/image";
import submarineImage from "@/app/images/images/submarine.png";
import styles from "./history.module.css";
import { CheckCircle2, Clock, Globe, MoreVertical , XCircle,} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {Card , CardContent} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils"

const scanTypeLabel: Record<string, string> = {
    active_vulnerability: "Active Vulnerability Scan",
    passive_ctem: "Passive Reconnaissance",
};

const statusConfig: Record<string, { label: string; className: string; icon: LucideIcon }> = {
    running: { label: "Running", className: "border-brand-cyan text-brand-cyan bg-brand-cyan/10" ,icon: Globe },
    queued: { label: "Queued", className: "border-brand-yellow text-brand-yellow bg-brand-yellow/10", icon: Clock},
    completed: {label: "Completed", className: "border-brand-success text-brand-success bg-brand-success/10", icon: CheckCircle2},
    failed: {label: "Failed", className: "border-brand-alert text-brand-alert bg-brand-alert/10", icon: XCircle},
    partial: {label: "Partial", className: "border-brand-yellow text-brand-yellow bg-brand-yellow/10", icon: XCircle} ,
};

function StatusBadge({ status }: { status: string}) {
        const config = statusConfig[status] ?? statusConfig.queued;
        return (
            <div className="flex w-28 shrink-0 justify-center">
                <Badge variant = "outline" className={(cn("uppercase tracking-wide",config.className))}>
                    {config.label}                
                </Badge>
            </div>
            
    );
}

function ScanIcon ({ status }: { status: string}){
        const config = statusConfig[status] ?? statusConfig.queued;
        const Icon = config.icon;
        return(
            <div className ={cn("flex size-11 shrink-0 items-center justify-center rounded-full bg-muted",config.className)}>
                <Icon className = "size-5"/>
            </div>
        );
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
    <div className={styles.historyPage}>
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
              <div className="flex flex-col gap-3">
                {scans.map(scan => (
                  <Card
                    key={scan.id}
                    className="cursor-pointer border border-brand-panel-border bg-brand-panel ring-0"
                    onClick={e => openModal(scan, e)}
                  >

                    <CardContent className="flex flex-wrap items-center gap-4">
                      <ScanIcon status= {scan.status} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium text-foreground">{scan.domain}</p>
                        <p className="text-sm text-muted-foreground">
                            {scanTypeLabel[scan.scan_type] ?? scan.scan_type}
                        </p>
                      </div>
                      <StatusBadge status={scan.status}/>
                      <span className="w-40 shrink-0 text-sm text-muted-foreground">
                            {formatDate(scan.created_at)}
                      </span>
                          <Button
                          variant="ghost"
                          size="icon"
                          aria-label="More options"
                          onClick={e => openModal(scan, e)}
                        >
                          <MoreVertical className="size-4" />
                        </Button>
                      </CardContent>
              </Card>
         ))}
          </div>
          );
        })()}
      </div>

      {/* Row action modal */}
      {modal && (
      <>
        <button
          type="button"
          aria-label="Close modal"
          className={styles.modalBackdrop}
          onClick={closeModal}
        />

        <div
          className={styles.modal}
          data-modal
          role="dialog"
          tabIndex={0}
          onClick={e => e.stopPropagation()}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              closeModal();
            }
          }}
          style={dragPos ? { left: dragPos.x, top: dragPos.y, transform: "none" } : undefined}
        >
          <button
            type="button"
            className={styles.modalDomain}
            onMouseDown={startDrag}
          >
            {modal.domain}
          </button>

          <button
            type="button"
            className={`${styles.modalBtn} ${styles.modalBtnReport}`}
            onClick={() => { closeModal(); router.push(`/phase2_scan/results/${modal.id}`); }}
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
            type="button"
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
