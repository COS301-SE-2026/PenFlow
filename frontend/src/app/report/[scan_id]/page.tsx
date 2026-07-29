"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import NavBar from "@/components/NavBar";
import { Input } from "@/components/ui/input";
import { Chart as ChartJS, ArcElement, Tooltip, Legend, type ChartOptions } from "chart.js";
import ChartDataLabels from "chartjs-plugin-datalabels";
import { Doughnut } from "react-chartjs-2";
import { fetchScanSummary, getReportPdfUrl, SEVERITY_COLORS, formatDate, sendReportEmail } from "@/lib/scanService";
import type { ExecutiveSummary } from "@/lib/scanService";
import styles from "./report.module.css";

ChartJS.register(ArcElement, Tooltip, Legend, ChartDataLabels);


const pieOptions: ChartOptions<"doughnut"> = {
  cutout: "65%",
  layout: { padding: 60 },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: "#091628",
      borderColor: "rgba(43,180,220,0.3)",
      borderWidth: 1,
      titleColor: "#e5f3ff",
      bodyColor: "#e5f3ff",
    },
    datalabels: {
      display: true,
      color: "#e5f3ff",
      font: { size: 12, family: "Rajdhani, sans-serif" },
      anchor: "end",
      align: "end",
      offset: 8,
      formatter: (value: number, ctx) => {
        const label = ctx.chart.data.labels?.[ctx.dataIndex] as string ?? "";
        return `${label} - ${value}`;
      },
    },
  },
  maintainAspectRatio: false,
};

function SeverityBadge({ severity }: Readonly<{ severity: string }>) {
  const s = severity.toLowerCase();
  return (
    <span
      className={styles.badge}
      style={{ backgroundColor: SEVERITY_COLORS[s] ?? "#4a7a9b" }}
    >
      {severity.toUpperCase()}
    </span>
  );
}


export default function ReportPage() {
  const { scan_id } = useParams<{ scan_id: string }>();
  const [data, setData] = useState<ExecutiveSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [email, setEmail] = useState("");
  const [sendStatus, setSendStatus] = useState<"idle" | "sent">("idle");

  useEffect(() => {
    setMounted(true);
    fetchScanSummary(scan_id)
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Unknown error"));
  }, [scan_id]);

  if (!data) {
    return (
      <div className={styles.reportPage}>
        <NavBar />
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

  const { scan_summary, risk_snapshot, top_findings, asset_impact, report_status } = data;

  const severityNames = ["critical", "high", "medium", "low", "info"];
  const rawCounts = [
    risk_snapshot.critical_count,
    risk_snapshot.high_count,
    risk_snapshot.medium_count,
    risk_snapshot.low_count,
    risk_snapshot.info_count,
  ];
  const pieEntries = severityNames
    .map((name, i) => ({ label: name[0].toUpperCase() + name.slice(1), value: rawCounts[i], color: SEVERITY_COLORS[name] }))
    .filter(d => d.value > 0);

  const chartData = {
    labels: pieEntries.map(d => d.label),
    datasets: [{
      data: pieEntries.map(d => d.value),
      backgroundColor: pieEntries.map(d => d.color),
      borderWidth: 0,
    }],
  };


  const canDownload = report_status?.pdf_path != null;
  const pdfUrl = getReportPdfUrl(scan_id);

  const handleSendReport = async (e: React.FormEvent) => {
  e.preventDefault();

  if (!email.trim()) return;

  try {
    await sendReportEmail(scan_id, email);
    setSendStatus("sent");
  } catch (err) {
    console.error(err);
    alert("Failed to send report email");
  }
};

  return (
    <div className={styles.reportPage}>
      <NavBar />

      {/* Hero — same wave + submarine graphic as home page */}
      <section className={styles.hero}>
        <div className={styles.heroTextWrap}>
          <h1>REPORT SUMMARY</h1>
          <p className={styles.heroDomain}>{scan_summary.domain.toUpperCase()}</p>
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
        <div className={styles.grid2}>
          {/* Findings by Severity */}
          <div className={styles.card}>
            <span className={styles.cardLabel}>FINDINGS BY SEVERITY</span>
            {pieEntries.length > 0 ? (
              <div style={{ height: 320 }}>
                {mounted && <Doughnut data={chartData} options={pieOptions} />}
              </div>
            ) : (
              <p className={styles.emptyText}>No findings recorded.</p>
            )}
          </div>

          {/* Exposed Assets */}
          <div className={styles.card}>
            <span className={styles.cardLabel}>EXPOSED ASSETS</span>
            {asset_impact.asset_type_breakdown.length === 0 ? (
              <p className={styles.emptyText}>No assets recorded.</p>
            ) : (
              asset_impact.asset_type_breakdown.map(row => (
                <div key={row.asset_type} className={styles.assetRow}>
                  <span className={styles.assetLabel}>
                    {row.asset_type.replace(/_/g, " ").toUpperCase()}
                  </span>
                  <span className={styles.assetCount}>{row.total_assets}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Top Findings table */}
        <div className={styles.card}>
          <span className={styles.cardLabel}>TOP FINDINGS</span>
          {top_findings.length === 0 ? (
            <p className={styles.emptyText}>No findings recorded.</p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table className={styles.findingsTable}>
                <thead>
                  <tr>
                    <th>SEVERITY</th>
                    <th>FINDING</th>
                    <th>SOURCE</th>
                    <th>DATE</th>
                  </tr>
                </thead>
                <tbody>
                  {top_findings.map(f => (
                    <tr key={f.id}>
                      <td><SeverityBadge severity={f.severity} /></td>
                      <td>{f.title}</td>
                      <td className={styles.mutedText}>{f.source}</td>
                      <td className={styles.mutedText}>{formatDate(f.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Bottom bar — download + email */}
        <div className={styles.bottomBar}>
          {canDownload ? (
            <a href={pdfUrl} className={styles.downloadBtn} download>
              ↓ DOWNLOAD FULL REPORT
            </a>
          ) : (
            <span className={`${styles.downloadBtn} ${styles.downloadBtnDisabled}`}>
              ↓ DOWNLOAD FULL REPORT
            </span>
          )}

          <form className={styles.emailRow} onSubmit={handleSendReport}>
            <Input
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className={styles.emailInput}
              disabled={sendStatus === "sent"}
            />
            <button
              type="submit"
              className={`${styles.sendBtn} ${email.trim() && sendStatus !== "sent" ? styles.sendBtnActive : ""}`}
              disabled={!email.trim() || sendStatus === "sent"}
            >
              {sendStatus === "sent" ? "SENT ✓" : "SEND REPORT"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
