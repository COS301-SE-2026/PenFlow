const PORTS = [
  {port: "80", service: "HTTP", open: true, severity:"medium", label: "MEDIUM"},
  {port: "443", service: "HTTPS", open: true, severity:"info", label: "INFO"},
  {port: "22", service: "SSH", open: true, severity:"high", label: "HIGH"},
  {port: "3306", service: "MySQL", open: true, severity:"critical", label: "CRITICAL"},
  {port: "8080", service: "HTTP-ALT", open: false, severity:"low", label: "LOW"},
]

export default function Phase2Content() {
  return (
    <>
      {}
      <div className={styles.phaseContent}>
        <div className={styles.phaseCopyWrap}>
          <h2 className={styles.phaseHeading}>EXTERNAL VULNERABILITY SCAN</h2>
          <p className={styles.phaseBody}>
            Following initial discovery, Penflow enables authorised users to perform controlled,
            external vulnerability scans. This scan is restricted to the external perimeter - 
            focusing on open ports, service configurations, TLS settings, and known vulnerabilites.
            </p>
        </div>
        <div className={styles.phaseVisual}>
          <div className={styles.visual}>
            <div className={styles.terminalBar}>
              <span className={styles.termTitle}>PERIMETER SCAN - YOUR DOMAIN</span>
            </div>
            <div className={styles.terminalBody}>
              <div className={styles.portHeader}>
                <span>PORT</span><span>SERVICE</span><span>STATUS</span><span>SEVERITY </span>
              </div>
              {PORTS.map((row) => (
                <div key={row.port} className={styles.portRow}>
                  <span className={styles.portNum}>{row.port}</span>
                  <span className={styles.portService}>{row.service}</span>
                  <span className={styles.portStatus} data-open={row.open}>{row.open ? "OPEN" : "FILTERED"}</span>
                  <span className={styles.badge} data-sev={row.severity}>{row.label}</span>
                </div>
              ))}
            </div>
          </div>
      </div>
    </>
  )
}