import styles from "./Phase3Content.module.css";

const LOG = [
  { time: "09:14", actor: "SYSTEM",    msg: "Engagement OP-2025-047 initialised" },
  { time: "09:21", actor: "CLIENT",    msg: "Scope defined - 14 assets submitted" },
  { time: "10:03", actor: "PENTESTER",    msg: "Recon phase started" },
  { time: "11:46", actor: "PENTESTER",    msg: "Critical finding: RCE on api.target.com" },
  { time: "12:05", actor: "CLIENT",    msg: "Finding acknowledgeed - remediation assigned" },
  { time: "14:30", actor: "AUDITOR",    msg: "Audi trail verified - report signed off" },
]

export default function Phase3Content() {
  return (
    <div className={styles.phaseContent}>
      <div className={styles.phaseCopyWrap}>
        <h2 className={styles.phaseHeading}>BRING IN THE EXPERTS</h2>
        <p className={styles.phaseBody}>
          THE FINAL PHASE TRANSFORMS PENFLOW INTO A MANAGED PENETRATION TESTING
          COORDINATION PLATFORM. DEFINE YOUR ENGAGEMENT SCOPE, ASSIGN PENTESTERS,
          AND MONITOR PROGRESS THROUGH A DEDICATED COMMAND DASHBOARD.
        </p>
        <p className={styles.phaseBody}>
          PENTESTERS SUBMIT FINDINGS DIRECTLY IN-PLATFORM - LINKED TO SPECIFIC
          ASSETS AND IMMEDIATELY AVAILABLE FOR CLIENT REVIEW.
          ROLE-BASED ACCESS CONTROL AND AUDIT LOGGING ENSURE EVERY ACTION IS TRACEABLE.
        </p>
      </div>

      <div className={styles.phaseVisual}>
        <div className={styles.visual}>
          <div className={styles.terminalBar}>
            <span className={styles.termDot} data-col="red" />
            <span className={styles.termDot} data-col="yellow" />
            <span className={styles.termDot} data-col="green" />
            <span className={styles.termTitle}>LIVE DASHBOARD</span>
      </div>
          <div className={styles.statusRow}>
            <div className={styles.statusCard} data-col = "success">
              <span className={styles.statusVal}>14</span>
              <span className={styles.statusKey}>ASSETS IN SCOPE</span>
            </div>
            <div className={styles.statusCard} data-col = "alert">
              <span className={styles.statusVal}>3</span>
              <span className={styles.statusKey}>CRITICAL FINDINGS</span>
            </div>
            <div className={styles.statusCard} data-col = "cyab">
              <span className={styles.statusVal}>LIVE</span>
              <span className={styles.statusKey}>ENGAGEMENT STATUS</span>
            </div>
          </div>
          <div className={styles.logWrap}>
            {LOG.map((entry) => (
              <div key={entry.time} className={styles.logRow}>
                <span className={styles.logTime}>{entry.time}</span>
                <span className={styles.logActor} data-actor={entry.actor.toLowerCase()}>{entry.actor}</span>
                <span className={styles.logMsg}>{entry.msg}</span>
              </div>
            ))}
            <div className={styles.cursor}> </div>
          </div>
        </div>
      </div>
    </div>
  );
}