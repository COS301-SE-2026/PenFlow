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
    </div>


    {}
    <div className={styes.phaseContent}>
      <div className={styles.phaseCopyWrap}>
        <h2 className={styles.phaseHeading}>SECURE ACCESS</h2>
        <p className={styles.phaseBody}>
          Before any active scan occurs, the system enforces a domain ownership verfication process.
          This ensures that only legitamate asset owners can initiate scans.
          This guarantees that every assessment statys within authorised boundaries.
        </p>
        <p className={styles.phaseBody}>
          Scans are executed as isolated background jobs within containerised environments, 
          preventing cross-client data leakage and ensuring secure execution. Findings are enhanced through
          integration with vulnerability databases and assigned severity levels to support prioritisation.
        </p>
      </div>
      <div className={styles.phaseVisual}>
        <svg viewBox="0 0 320 220" xmlns="http://www.w3.org/2000/svg" className={styles.secureSvg}> 
        {/* Computer frame */}
        <rect x="20" y="12" width="280" height="196" rx="12" fill="☐rgba(6,14,28,0.97)" stroke="rgba(43,216,245,0.2)" strokeWidth="1.5"/> 
        <rect x="20" y="12" width="280" height="28" rx="12" fill="Orgba(13,30,58,0.95)"/>
        <rect x="20" y="28" width="280" height="12" fill="rgba(13,30,58,0.95)"/>
        <circle cx="38" cy="26" r="5" fill="#ff5f4e"/>
        <circle cx="54" cy="26" r="5" fill="■■ #f5c842"/>
        <circle cx="70" cy="26" r="5" fill="■ #4ade80"/>
        <rect x="90" y="18" width="160" height="16" rx="4" fill="rgba(43,216,245,0.07)" stroke="rgba(43,216,245,0.2)" strokeWidth="1"/> 
        <text x="170" y="30" textAnchor="middle" fill="Orgba(43,216,245,0.45)" fontSize="8" fontFamily="monospace">domain verification</text> 
        {/* scan animation */}
        <text x="160" y="62" textAnchor="middle" fill="#ff5f4e" fontSize="15" fontFamily="monospace" fontWeight="bold" letterSpacing="5"> 
          SCAN
          <animate attributeName="opacity" values="1;0.35;1" dur="1.1s" repeatCount="indefinite",
        </text>
        {/* barcode scanner frame */}
        {["M88,82 L88,66 L104,66","M232,82 L232,66 L216,66","M88,172 L88,188 L104,188","M232,172 L232,188 L216,188"].map((d, i) => ( 
        <path key={i} d={d} fill="none" stroke="#ff5f4e" strokeWidth="3" strokeLinecap="round">
          <animate attributeName="opacity" values="1;0.4;1" dur="1.1s" repeatCount="indefinite"/>
        </path>
      ))}
      {/* Moving scan Line */}
      <line x1="88" y1="66" x2="232" y2="66" stroke="rgba(255,95,78,0.55)" strokeWidth="1.5"> 
        <animate attributeName="y1" values="66;188;66" dur="2s" repeatCount="indefinite"/> 
        <animate attributeName="y2" values="66;188;66" dur="2s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0;0.8;0.8;0" dur="2s" repeatCount="indefinite"/> 
      </line>
      {/* Shield */}
      <path d="M160,80 L184,91 L184,123 Q184,143 160,154 Q136,143 136,123 L136,91 Z" fill="□rgba(10,40,25,0.8)" stroke="rgba(74,222,128,0.75)" strokeWidth="2"/> 
      <polyline points="148,116 158,127 174,104" stroke="#4ade80" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/> 
      {/* User circle */}
      <circle cx="196" cy="94" r="22" fill="rgba(6,14,28,0.97)" stroke="rgba(43,216,245,0.5)" strokeWidth="1.5"/>
      <circle cx="196" cy="87" r="7" fill="rgba(43,180, 220,0.7)"/>
      <path d="M180,108 Q196,101 212,108" stroke="rgba(43,180,220,0.65)" strokeWidth="2" fill="Orgba(43,180,220,0.2)" strokeLinecap="round"/> 
      {/* Verified badge */}
      <rect x="118" y="162" width="84" height="18" rx="5" fill="rgba(10,40, 25,0.5)" stroke="rgba(74,222,128,0.5)" strokeWidth="1"/>
      <text x="160" y="174" textAnchor="middle" fill="☐ rgba(74,222,128,0.95)" fontSize="9" fontFamily="monospace" letterSpacing="1">✓ VERIFIED</text> 
      {/* Laptop base */}
      <rect x="10" y="208" width="300" height="8" rx="4" fill="☐rgba(13,30,58,0.9)" stroke="rgba(43,216,245,0.15)" strokeWidth="1"/> 
      <rect x="120" y="216" width="80" height="4" rx="2" fill="rgba(43,216,245,0.06)"/>
    </svg>
  </div>
</div>

    </>
  )
}