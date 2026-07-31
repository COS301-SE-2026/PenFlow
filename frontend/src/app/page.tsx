import NavBar from "@/components/NavBar";
import Image from "next/image";
import submarineImage from "@/app/images/images/submarine.png";
import DangerSection from "@/shared/components/DangerSection";
import SonarSection from "@/shared/components/SonarSection";
import SafetySection from "@/shared/components/SafetySection";
import ScanConsoleSection from "@/app/scan/components/ScanConsoleSection";
import OsintPanel from "@/shared/components/sections/OsintPanel";
import Phase2Content from "@/shared/components/sections/Phase2Content";
import Phase3Content from "@/shared/components/sections/Phase3Content";
import styles from "@/shared/components/page.module.css";

export default function Home() {
  return (
    <main className="landing">
      <NavBar />

      <section className="hero">
        <div className="heroTextWrap">
          <h1>PENFLOW</h1>
          <p>
            To level the playing field in cybersecurity — giving small and medium
            businesses the same continuous threat visibility and testing capabilities
            previously reserved for enterprise organisations.
          </p>
        </div>

        <div className="waterline" aria-hidden="true">
          <svg
            viewBox="0 0 1440 200"
            xmlns="http://www.w3.org/2000/svg"
            className="absolute inset-0 w-full h-full"
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
            className="submarine"
            priority
          />
        </div>
      </section>

      <div className={styles.pipeline}>
        

        <div className={styles.phaseLabel} data-first="true">
          <span className={styles.phaseNum}>PHASE 1</span>
          <span className ={styles.phaseTitle}>DISCOVER</span>
        </div>
        <DangerSection />
        <SonarSection />
        <div className={styles.safetyOsintRow}>
          <SafetySection/>
          <OsintPanel/>
        </div>
        <ScanConsoleSection/>

        <div className={styles.phaseLabel}>
          <span className={styles.phaseNum}>PHASE 2</span>
          <span className ={styles.phaseTitle}>ANALYSE</span>
        </div>
        <Phase2Content/>

        <div className={styles.phaseLabel}>
          <span className={styles.phaseNum}>PHASE 3</span>
          <span className ={styles.phaseTitle}>REACT</span>
        </div>
        <Phase3Content/>
      </div>
    </main>
  );
}
