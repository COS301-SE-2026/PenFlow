import Image from "next/image";
import subMissileImage from "@/app/images/images/SubMissile.png";
import styles from "./DangerSection.module.css";

export default function DangerSection() {
  return (
    <section className={styles.dangerSection}>
      <div className={styles.dangerCopy}>
        <h2>IS YOUR DOMAIN IN DANGER?</h2>
        <p>
          ATTACKERS DO NOT NEED CREDENTIALS TO START PROFILING YOUR
          ORGANISATION. FORGOTTEN SUBDOMAINS, LEAKED METADATA, EXPOSED SERVICES,
          AND PUBLIC RECORDS CAN QUIETLY REVEAL WHERE TO AIM NEXT.
        </p>
        <p>
          WITHOUT REGULAR CTEM SCANS, SMALL PUBLIC CLUES CAN BECOME A MAP FOR
          PHISHING, IMPERSONATION, ASSET DISCOVERY, AND TARGETED INTRUSION
          ATTEMPTS BEFORE YOU REALISE THE EXPOSURE EXISTS.
        </p>
      </div>

      <div className={styles.dangerImageWrap} aria-hidden="true">
        <Image
          src={subMissileImage}
          alt=""
          width={420}
          height={420}
          className={styles.dangerImage}
        />
      </div>
    </section>
  );
}
