import Image from "next/image";
import safetyImage from "@/app/images/images/safety image.png";
import styles from "./SafetySection.module.css";

export default function SafetySection() {
  return (
    <section className={styles.safeSection}>
      <div className={styles.safeCopy}>
        <h2>100% SAFE &amp; PASSIVE</h2>
        <p>
          WE DON&apos;T TOUCH YOUR SYSTEM. OUR SCAN USES TRUSTED THIRD-PARTY
          SOURCES AND OPEN DATA, ENSURING LEGAL COMPLIANCE AND ZERO RISK TO YOUR
          ENVIRONMENT.
        </p>
        <p>
          WE WILL GENERATE YOU AN EASY-TO-UNDERSTAND REPORT INSTANTLY, NO
          ACCOUNT NEEDED! DISCOVER WHAT ATTACKERS CAN SEE ABOUT YOUR
          ORGANISATION NOW.
        </p>
      </div>

      <div className={styles.safeImageWrap} aria-hidden="true">
        <Image
          src={safetyImage}
          alt=""
          width={380}
          height={380}
          className={styles.safeImage}
        />
      </div>
    </section>
  );
}
